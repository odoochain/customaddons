from odoo import fields, models, api
# from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ['mail.thread', 'account.payment']

    name = fields.Char(readonly=False)
    state = fields.Selection(track_visibility='always')
    amount = fields.Monetary(track_visibility='always')
    partner_id = fields.Many2one(track_visibility='always')
    journal_id = fields.Many2one(track_visibility='always')
    destination_journal_id = fields.Many2one(track_visibility='always')
    currency_id = fields.Many2one(track_visibility='always')
    # campo a ser extendido y mostrar un nombre detemrinado en las lineas de
    # pago de un payment group o donde se desee (por ej. con cheque, retención,
    # etc)
    payment_method_description = fields.Char(
        compute='_compute_payment_method_description',
        string='Payment Method',
    )

    @api.multi
    def _compute_payment_method_description(self):
        for rec in self:
            rec.payment_method_description = rec.payment_method_id.display_name

    # nuevo campo funcion para definir dominio de los metodos
    payment_method_ids = fields.Many2many(
        'account.payment.method',
        compute='_compute_payment_methods',
        string='Available payment methods',
    )
    journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_journals'
    )
    # journal_at_least_type = fields.Char(
    #     compute='_compute_journal_at_least_type'
    # )
    destination_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_destination_journals'
    )

    @api.multi
    @api.depends(
        # 'payment_type',
        'journal_id',
    )
    def _compute_destination_journals(self):
        for rec in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                # al final pensamos mejor no agregar esta restricción, por ej,
                # para poder transferir a tarjeta a pagar. Esto solo se usa
                # en transferencias
                # ('at_least_one_inbound', '=', True),
                ('company_id', '=', rec.journal_id.company_id.id),
                ('id', '!=', rec.journal_id.id),
            ]
            rec.destination_journal_ids = rec.journal_ids.search(domain)

    # @api.multi
    # @api.depends(
    #     'payment_type',
    # )
    # def _compute_journal_at_least_type(self):
    #     for rec in self:
    #         if rec.payment_type == 'inbound':
    #             journal_at_least_type = 'at_least_one_inbound'
    #         else:
    #             journal_at_least_type = 'at_least_one_outbound'
    #         rec.journal_at_least_type = journal_at_least_type

    @api.multi
    def get_journals_domain(self):
        """
        We get domain here so it can be inherited
        """
        self.ensure_one()
        domain = [('type', 'in', ('bank', 'cash'))]
        if self.payment_type == 'inbound':
            domain.append(('at_least_one_inbound', '=', True))
        # Al final dejamos que para transferencias se pueda elegir
        # cualquier sin importar si tiene outbound o no
        # else:
        elif self.payment_type == 'outbound':
            domain.append(('at_least_one_outbound', '=', True))
        return domain

    @api.multi
    @api.depends(
        'payment_type',
    )
    def _compute_journals(self):
        for rec in self:
            rec.journal_ids = rec.journal_ids.search(rec.get_journals_domain())

    @api.multi
    @api.depends(
        'journal_id.outbound_payment_method_ids',
        'journal_id.inbound_payment_method_ids',
        'payment_type',
    )
    def _compute_payment_methods(self):
        for rec in self:
            if rec.payment_type in ('outbound', 'transfer'):
                methods = rec.journal_id.outbound_payment_method_ids
            else:
                methods = rec.journal_id.inbound_payment_method_ids
            rec.payment_method_ids = methods

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """
        Sobre escribimos y desactivamos la parte del dominio de la funcion
        original ya que se pierde si se vuelve a entrar
        """
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
            else:
                self.partner_type = False
            # limpiamos journal ya que podria no estar disponible para la nueva
            # operacion y ademas para que se limpien los payment methods
            self.journal_id = False
        # # Set payment method domain
        # res = self._onchange_journal()
        # if not res.get('domain', {}):
        #     res['domain'] = {}
        # res['domain']['journal_id'] = self.payment_type == 'inbound' and [
        #     ('at_least_one_inbound', '=', True)] or [
        #     ('at_least_one_outbound', '=', True)]
        # res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        # return res

    # @api.onchange('partner_type')
    def _onchange_partner_type(self):
        """
        Agregasmos dominio en vista ya que se pierde si se vuelve a entrar
        Anulamos funcion original porque no haria falta
        """
        return True

    @api.onchange('journal_id')
    def _onchange_journal(self):
        """
        Sobre escribimos y desactivamos la parte del dominio de la funcion
        original ya que se pierde si se vuelve a entrar
        """
        if self.journal_id:
            self.currency_id = (
                self.journal_id.currency_id or self.company_id.currency_id)
            # Set default payment method
            # (we consider the first to be the default one)
            payment_methods = (
                self.payment_type == 'inbound' and
                self.journal_id.inbound_payment_method_ids or
                self.journal_id.outbound_payment_method_ids)
            # si es una transferencia y no hay payment method de origen,
            # forzamos manual
            if not payment_methods and self.payment_type == 'transfer':
                payment_methods = self.env.ref(
                    'account.account_payment_method_manual_out')
            self.payment_method_id = (
                payment_methods and payment_methods[0] or False)
            # si se eligió de origen el mismo diario de destino, lo resetiamos
            if self.journal_id == self.destination_journal_id:
                self.destination_journal_id = False
        #     # Set payment method domain
        #     # (restrict to methods enabled for the journal and to selected
        #     # payment type)
        #     payment_type = self.payment_type in (
        #         'outbound', 'transfer') and 'outbound' or 'inbound'
        #     return {
        #         'domain': {
        #             'payment_method_id': [
        #                 ('payment_type', '=', payment_type),
        #                 ('id', 'in', payment_methods.ids)]}}
        # return {}

    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        """
        We send force_company on context so payments can be created from parent
        companies. We try to send force_company on self but it doesnt works, it
        only works sending it on partner
        """
        res = super(AccountPayment, self)._compute_destination_account_id()
        for rec in self.filtered(
                lambda x: not x.invoice_ids and x.payment_type != 'transfer'):
            partner = rec.partner_id.with_context(
                force_company=rec.company_id.id)
            if rec.partner_type == 'customer':
                rec.destination_account_id = (
                    partner.property_account_receivable_id.id)
            else:
                rec.destination_account_id = (
                    partner.property_account_payable_id.id)

            if not (rec.partner_type and rec.destination_account_id):
                aml = rec.env['account.move.line'].search([('payment_id', '=', rec.id),
                                                            ('account_id', 'not in',
                                                             [rec.journal_id.default_debit_account_id.id,
                                                              rec.journal_id.default_credit_account_id.id])], limit=1)
                if aml:
                    rec.destination_account_id = aml.account_id
                else:
                    rec.destination_account_id = rec.journal_id.default_debit_account_id or\
                                                 rec.journal_id.default_credit_account_id
        return res
