from odoo import models, fields, api, _
import logging
import requests

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def _cron_parse_currencies(self):
        _logger.info("Parsing UAH to currencies.")

        companies = self.env["res.company"].search([("currency_id.name", "=", "UAH")])

        if not companies:
            _logger.error("No Companies with UAH currencies. Skipping.")
            return False
        
        currencies = self.search([
                ("active", "=", True),
                ("name", "!=", "UAH")
            ])

        if not currencies:
            _logger.info("No active foreign currencies to update.")
            return True

        nbu_rates = self._get_nbu_rates()
        if not nbu_rates:
            _logger.error("Couldn't retrieve rates from NBU. Aborting cron.")
            return False

        self._update_currencies_daily_rate(nbu_rates, companies, currencies)
        _logger.info("Currency rates successfully updated.")

        return True

    def _get_nbu_rates(self):
        url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"

        try:
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
        except Exception as e:
            _logger.error("Failed to fetch rates from NBU API: %s", e)
            return {}
        
        rates_dict = {item["cc"] : item["rate"] for item in data if "cc" in item and "rate" in item}
        
        return rates_dict
    
    def _get_odoo_rate(self, nbu_rate):
        return 1.0 / nbu_rate
    
    def _get_existing_rates_map(self, currencies, companies, date):
        existing_rates = self.env["res.currency.rate"].search([
            ("currency_id", "in", currencies.ids),
            ("company_id", "in", companies.ids),
            ("name", "=", date),
        ])

        rate_map = {(r.currency_id.id, r.company_id.id): r for r in existing_rates}
        return rate_map

    def _prepare_rate_changes(self, nbu_rates, companies, currencies, date, rate_map):
        to_create = []
        to_update = {}

        for cc in currencies:
            nbu_rate = nbu_rates.get(cc.name)
            if not nbu_rate or nbu_rate <= 0:
                continue
            odoo_rate = self._get_odoo_rate(nbu_rate)

            existing_for_currency = self.env["res.currency.rate"]
            for company in companies:
                existing = rate_map.get((cc.id, company.id))
                if existing:
                    existing_for_currency |= existing
                else:
                    to_create.append({
                        "currency_id": cc.id,
                        "name": date,
                        "rate": odoo_rate,
                        "company_id": company.id,
                    })

            if existing_for_currency:
                to_update[cc.id] = (odoo_rate, existing_for_currency)

        return to_create, to_update

    def _apply_rate_changes(self, to_create, to_update):
        for odoo_rate, records in to_update.values():
            records.write({"rate": odoo_rate})

        if to_create:
            self.env["res.currency.rate"].create(to_create)

    def _update_currencies_daily_rate(self, nbu_rates, companies, currencies, date=None):
        if not nbu_rates or not companies or not currencies:
            return True
        date = date or fields.Date.today()
        rate_map = self._get_existing_rates_map(currencies, companies, date)
        to_create, to_update = self._prepare_rate_changes(
                nbu_rates, companies, currencies, date, rate_map
            )
        self._apply_rate_changes(to_create, to_update)
        return True

    def action_open_history_wizard(self):
        self.ensure_one()
        return {
            "name": _("Fetch Rate History"),
            "type": "ir.actions.act_window",
            "res_model": "fetch.history.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_currency_id": self.id,
            },
        }
