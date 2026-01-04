from odoo import models, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    def write(self, vals):
        prev_states = {po.id: po.state for po in self}
        res = super().write(vals)

        # Trigger only when state changes to 'purchase'
        if vals.get('state') == 'purchase':
            for po in self:
                if prev_states.get(po.id) != 'purchase':
                    po._notify_groups_on_po_confirm()

        return res

   

    def _notify_groups_on_po_confirm(self):
        privilege = self.env['res.groups'].search(
            [('privilege_id.name', '=', 'Protectol Finance')],
            limit=1
        )

    
        if privilege:
            template = self.env.ref('sandy_custom_changes.mail_template_purchase_order')
            template.sudo().send_mail(self.id, force_send=True)



        

