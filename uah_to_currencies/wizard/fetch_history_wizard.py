from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.fields import Command
import logging
import requests

_logger = logging.getLogger(__name__)

class FetchHistoryWizard(models.TransientModel):
    _name = "fetch.history.wizard"
    _description = "Wizard to fetch currency history"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        domain="[('name','!=','UAH'),('active','=',True)]"
    )
    top_date = fields.Date(required=True, default=fields.Date.today)
    bottom_date = fields.Date(required=True,
                              default=lambda self:fields.Date.today() - timedelta(days=7))

    def _get_currency_history(self):
        currency_code = self.currency_id.name
        _logger.info("Parsing %s history.", currency_code)
        url = "https://bank.gov.ua/NBU_Exchange/exchange_site?start={}&end={}&valcode={}&sort=exchangedate&order=desc&json"

        start = str(self.bottom_date).replace("-", "")
        end = str(self.top_date).replace("-", "")

        url = url.format(start,end,currency_code)

        try:
            response = requests.get(url)
            response.raise_for_status()
                    
            data = response.json()
            return data
        
        except Exception as e:
            _logger.error("Failed to fetch history rates from NBU API for %s: %s", currency_code, e)
            return []
        
    def _process_history(self, raw_history):
        history = {
            datetime.strptime(item.get("exchangedate"), "%d.%m.%Y").date(): item.get("rate", None)
            for item in raw_history
        }
        return history
    
    def _get_existing_rate_map(self, companies):
        existing_rates = self.env["res.currency.rate"].search([
            ("currency_id", "=", self.currency_id.id),
            ("company_id", "in", companies.ids),
            ("name", "<=", self.top_date),
            ("name", ">=", self.bottom_date),
        ])

        rate_map = {(r.name, r.company_id.id): r for r in existing_rates}
        return rate_map
    
    def _get_odoo_rate(self, nbu_rate):
        return 1.0 / nbu_rate
    
    def _prepare_rate_changes(self, companies, rate_map, history):
        to_create = []
        to_update = {}

        for date, nbu_rate in history.items():
            if not nbu_rate or nbu_rate <= 0:
                continue
            odoo_rate = self._get_odoo_rate(nbu_rate)

            existing_for_currency = self.env["res.currency.rate"]
            for company in companies:
                existing = rate_map.get((date,company.id))
                if existing:
                    existing_for_currency |= existing
                else:
                    to_create.append({
                        "currency_id": self.currency_id.id,
                        "name": date,
                        "rate": odoo_rate,
                        "company_id": company.id,
                    })
            if existing_for_currency:
                to_update[date] = (odoo_rate, existing_for_currency)

        return to_create, to_update
    
    def _apply_rate_changes(self, to_create, to_update):
        for odoo_rate, records in to_update.values():
            records.write({"rate": odoo_rate})

        if to_create:
            self.env["res.currency.rate"].create(to_create)

    def action_apply(self):
        self.ensure_one()

        if self.bottom_date > self.top_date:
            raise UserError(_("Bottom date can not be after Top date"))
        if self.top_date > fields.Date.today():
            raise UserError(_("Top date can not be in future."))

        companies = self.env.companies.filtered(lambda c: c.currency_id.name == "UAH")

        if not companies:
            raise UserError(_("Only for companies with UAH as main currency."))

        raw_history = self._get_currency_history()
        history = self._process_history(raw_history)
        rate_map = self._get_existing_rate_map(companies)
        to_create, to_update = self._prepare_rate_changes(companies, rate_map, history)
        self._apply_rate_changes(to_create, to_update)







        