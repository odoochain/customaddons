# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from collections import OrderedDict
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_published = fields.Boolean(
        string="Is Published",
        help="If checked, the product will be published on the website.",
        default=False,
    )

    public_description = fields.Html(
        "Description for e-Commerce",
        sanitize_attributes=False,
        translate=html_translate,
        copy=False,
    )

    website_attachment_ids = fields.Many2many(
        string="Website attachments",
        comodel_name="ir.attachment",
        help="Files publicly downloadable from the product eCommerce page.",
    )

    feature_line_ids = fields.One2many(
        comodel_name="product.template.feature.line",
        inverse_name="product_tmpl_id",
        string="Features",
    )

    def _prepare_product_attachments_table(self):
        """This method returns product attachments."""
        attachments = self.sudo().website_attachment_ids
        return attachments

    def action_fill_missing_product_attrs(self):
        """Fill missing product variants for published attribute values."""
        if len(self.product_variant_ids) == 1:
            raise ValidationError(
                _("You can not fill missing product of non" " variant product.")
            )

        tmpl_attribute_lines = self.attribute_line_ids.filtered(
            lambda x: x.attribute_id.allow_filling
        )
        required_attrs = tmpl_attribute_lines.mapped("attribute_id")
        filled_variant_ids = []

        for product in self.product_variant_ids:
            product_attrs = product.attribute_value_ids.mapped("attribute_id")
            if not all(x in product_attrs.ids for x in required_attrs.ids):
                missing_attrs = required_attrs - product_attrs
                for attr in missing_attrs:
                    tmpl_line = tmpl_attribute_lines.filtered(
                        lambda x: x.attribute_id == attr
                    )
                    default_attr_value = tmpl_line.default_value_id
                    if not default_attr_value:
                        raise ValidationError(
                            _("Set default value for attribute %s" % attr.name)
                        )
                    product.attribute_value_ids |= default_attr_value
                    tmpl_line.value_ids |= default_attr_value
                    filled_variant_ids.append(product.id)

        if not filled_variant_ids:
            raise ValidationError(_("No missing product variants found."))

        tree_view_id = self.env.ref("product.product_product_tree_view").id
        action = {
            "type": "ir.actions.act_window",
            "views": [(tree_view_id, "tree")],
            "view_mode": "tree,form",
            "name": _("Products"),
            "res_model": "product.product",
            "domain": "[('type', '=', 'product'), ('id', 'in', %s)]"
            % filled_variant_ids,
        }
        return action


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    default_value_id = fields.Many2one(
        string="Default Value",
        comodel_name="product.attribute.value",
        help="Default value for the attribute.",
    )

    allow_filling = fields.Boolean(
        string="Allow Filling",
        help="If checked, attribute values will be filled automatically",
        related="attribute_id.allow_filling",
        readonly=True,
    )

    def _prepare_categories_for_display(self):
        """
        This method adds feature lines to the product specifications.
        """
        res = super()._prepare_categories_for_display()
        ptal = res.get(self.env["product.attribute.category"], False)
        res[self.env["product.attribute.category"]] = []
        if ptal:
            tmpl_id = ptal[0].product_tmpl_id.sudo()
            #  Attributes first
            for line in ptal.filtered(lambda x: len(x.value_ids) > 0):
                res[self.env["product.attribute.category"]].append(line)

            ptfl = tmpl_id.feature_line_ids
            for line in ptfl.filtered(lambda x: len(x.value_ids) > 0):
                res[self.env["product.attribute.category"]].append(line)

        return res
