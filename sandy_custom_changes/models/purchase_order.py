from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
        ('external', 'Internal Procurement'),
      
    ],
    string="Purchase Type",
    default=False,
    readonly=True,
    tracking=True)


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        user = self.env.user

        if user.has_group('purchase.group_purchase_internal'):
            res['purchase_type'] = 'internal'
        elif user.has_group('purchase.group_purchase_external'):
            res['purchase_type'] = 'external'

        return res

    def button_confirm(self):
        for order in self:

            # Normal behavior if no multi-vendor selected
            if not order.vendor_ids:
                return super(PurchaseOrder, self).button_confirm()

            # Prevent duplicate generation
            if order.state != 'draft':
                continue

            # 1️⃣ Confirm ORIGINAL PO
            res = super(PurchaseOrder, order).button_confirm()

            # 2️⃣ Create & confirm vendor-wise POs
            for vendor in order.vendor_ids:
                po_vals = {
                    'partner_id': vendor.id,
                    'origin': order.name,
                    'order_line': [],
                }

                for line in order.order_line:
                    po_vals['order_line'].append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'product_uom_id': line.product_uom_id.id,
                        'date_planned': line.date_planned,
                    }))

                new_po = self.env['purchase.order'].create(po_vals)

                # Confirm vendor PO
                super(PurchaseOrder, new_po).button_confirm()

            return res

    