from odoo import models, fields, api, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection([
        ('draft','Draft'),
        ('sent','RFQ sent'),
        ('to_approve','To Approve'),
        ('purchase','Purchase Order'),
        ('waiting', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel','Cancelled'),
    ],)



    vendor_ids = fields.Many2many(
        'res.partner',
        'purchase_order_vendor_rel',
        'purchase_id',
        'partner_id',
        string='Vendors',
        help="Select multiple vendors"
    )

    purchase_type = fields.Selection([
        ('internal', 'Internal Procurement'),
        ('external', 'External Procurement'),

      
    ],
    string="Purchase Type",
    default=False,
    required=True,
    tracking=True)

    # Computed field to check if the current user is the administrator (ID 1)
    is_admin = fields.Boolean(
        string='Is Admin',
        compute='_compute_is_admin',
        store=False
        
    )

    @api.depends('purchase_type') # Add relevant dependency if needed, otherwise optional
    def _compute_is_admin(self):
        for record in self:
            # Check if the current user ID is the admin user ID (usually 1)
            if record.env.user.has_group('purchase.group_purchase_manager'):
                record.is_admin = True
            else:
                record.is_admin = False



    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        user = self.env.user

        if user.has_group('sandy_custom_changes.group_purchase_internal'):
            res['purchase_type'] = 'internal'
        elif user.has_group('sandy_custom_changes.group_purchase_external'):
            res['purchase_type'] = 'external'

        return res



    @api.model
    def create(self, vals):
       #  Create original RFQ
       order = super(PurchaseOrder, self).create(vals)
       # Always keep RFQ state
       order.state = 'draft'
       #  If no vendors selected → nothing else to do
       if not order.vendor_ids:
           return order
       #  Create duplicate RFQs for each vendor
       for vendor in order.vendor_ids:
           rfq_vals = {
               'partner_id': vendor.id,
               'origin': order.name,
               'state': 'draft',
               'order_line': [],
           }
           # Copy order lines
           for line in order.order_line:
               rfq_vals['order_line'].append((0, 0, {
                   'product_id': line.product_id.id,
                   'name': line.name,
                   'product_qty': line.product_qty,
                   'price_unit': line.price_unit,
                   'product_uom_id': line.product_uom_id.id,
                   'date_planned': line.date_planned,
                   'discount': line.discount,
                   'tax_ids': [(6, 0, line.tax_ids.ids)],
               }))
           super(PurchaseOrder, self).create(rfq_vals)
       return order



    def action_send_for_approval(self):
        for order in self:

            # 1. Vendor must be selected
            if not order.partner_id:
                raise ValidationError("Please select a Vendor before sending for approval.")

            # 2. Products must be added
            if not order.order_line:
                raise ValidationError("Add at least one product before sending for approval.")

            # 3. Amount must be greater than zero
            if order.amount_total <= 0:
                raise ValidationError("Total amount must be greater than 0 before approval.")

            # Passed all validations
            order.state = 'waiting'

    def button_confirm(self):
        for order in self:
            if order.state != 'approved':
                raise ValidationError("You cannot confirm the order until it is approved.")
        return super(PurchaseOrder, self).button_confirm()


    def action_send_for_approval(self):
        for order in self:
            if not order.partner_id:
                raise ValidationError(_("Please select a Vendor before sending for approval."))

            if not order.order_line:
                raise ValidationError(_("Please add at least one product."))

            if order.amount_total <= 0:
                raise ValidationError(_("Total amount must be greater than zero."))

            order.state = 'to_approve'

            # Internal notification
            order.message_post(
                body=_("Record waiting for approval.")
            )

    def action_reject(self):
        user = self.env.user

        if not (
            user.has_group('sandy_custom_changes.group_avp_admin') or
            user.has_group('sandy_custom_changes.group_finance')
        ):
            raise UserError(_("You are not authorized to reject this PO."))

        self.state = 'rejected'

        self.message_post(
            body=_("Purchase Order rejected by %s.") % user.name
        )

    def _get_approval_groups_in_sequence(self):
        return self.env['res.groups'].search(
            [('privilege_id.name', '=', 'Purchase Approvals')],
            order='id'
        )

    def action_approve(self):
        user = self.env.user

        if not (
            user.has_group('sandy_custom_changes.group_avp_admin') or
            user.has_group('sandy_custom_changes.group_finance')
        ):
            raise UserError(_("You are not authorized to approve this PO."))

        self.state = 'approved'

        # Convert to Purchase Order
        self.button_confirm()

        self.message_post(
            body=_("Purchase Order approved by %s.") % user.name
        )





    # def button_confirm(self):
    #     for order in self:

    #         # Normal behavior if no multi-vendor selected
    #         if not order.vendor_ids:
    #             return super(PurchaseOrder, self).button_confirm()

    #         # Prevent duplicate generation
    #         if order.state != 'draft':
    #             continue

    #         # 1️⃣ Confirm ORIGINAL PO
    #         res = super(PurchaseOrder, order).button_confirm()

    #         # 2️⃣ Create & confirm vendor-wise POs
    #         for vendor in order.vendor_ids:
    #             po_vals = {
    #                 'partner_id': vendor.id,
    #                 'origin': order.name,
    #                 'order_line': [],
    #             }

    #             for line in order.order_line:
    #                 po_vals['order_line'].append((0, 0, {
    #                     'product_id': line.product_id.id,
    #                     'name': line.name,
    #                     'product_qty': line.product_qty,
    #                     'price_unit': line.price_unit,
    #                     'product_uom_id': line.product_uom_id.id,
    #                     'date_planned': line.date_planned,

    #                 }))

    #             new_po = self.env['purchase.order'].create(po_vals)

    #             # Confirm vendor PO
    #             super(PurchaseOrder, new_po).button_confirm()

    #         return res

    