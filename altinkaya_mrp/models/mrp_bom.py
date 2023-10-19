# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class MRPBoM(models.Model):
    _inherit = "mrp.bom"

    bom_template_line_ids = fields.One2many(
        "mrp.bom.template.line", "bom_id", "BoM Template Lines"
    )

    def explode(self, product, quantity, picking_type=False):
        """
        This method is copied from mrp/models/mrp_bom.py
        and modified to use bom_template_line_ids within bom_line_ids
        """
        from collections import defaultdict

        graph = defaultdict(list)
        V = set()

        def check_cycle(v, visited, recStack, graph):
            visited[v] = True
            recStack[v] = True
            for neighbour in graph[v]:
                if visited[neighbour] == False:
                    if check_cycle(neighbour, visited, recStack, graph) == True:
                        return True
                elif recStack[neighbour] == True:
                    return True
            recStack[v] = False
            return False

        boms_done = [(self, {'qty': quantity, 'product': product, 'original_qty': quantity, 'parent_line': False})]
        lines_done = []
        V |= set([product.product_tmpl_id.id])

        bom_lines = [(bom_line, product, quantity, False, "bom_line") for bom_line in self.bom_line_ids]
        # Add bom template lines
        bom_lines += [(bom_line, product, quantity, False, "tmpl_line") for bom_line in self.bom_template_line_ids]
        for bom_line in self.bom_line_ids:
            V |= set([bom_line.product_id.product_tmpl_id.id])
            graph[product.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)

        # Add bom template lines
        for bom_line in self.bom_template_line_ids:
            V |= set([bom_line.product_tmpl_id.id])
            graph[product.product_tmpl_id.id].append(bom_line.product_tmpl_id.id)
        while bom_lines:
            current_line, current_product, current_qty, parent_line, line_type = bom_lines[0]
            bom_lines = bom_lines[1:]

            if current_line._skip_bom_line(current_product):
                continue

            line_quantity = current_qty * current_line.product_qty
            if line_type == "bom_line":
                line_product = current_line.product_id
            else:
                line_product = current_line._match_possible_variant(current_product)
                if not line_product:
                    continue

            bom = self._bom_find(products=line_product, picking_type=picking_type or self.picking_type_id, company_id=self.company_id.id)
            bom = bom[line_product]
            if bom.type == 'phantom':
                converted_line_quantity = current_line.product_uom_id._compute_quantity(line_quantity / bom.product_qty, bom.product_uom_id)
                bom_lines = [(line, current_line.product_id, converted_line_quantity, current_line) for line in bom.bom_line_ids] + bom_lines
                for bom_line in bom.bom_line_ids:
                    graph[current_line.product_id.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)
                    if bom_line.product_id.product_tmpl_id.id in V and check_cycle(bom_line.product_id.product_tmpl_id.id, {key: False for  key in V}, {key: False for  key in V}, graph):
                        raise UserError(_('Recursion error!  A product with a Bill of Material should not have itself in its BoM or child BoMs!'))
                    V |= set([bom_line.product_id.product_tmpl_id.id])
                boms_done.append((bom, {'qty': converted_line_quantity, 'product': current_product, 'original_qty': quantity, 'parent_line': current_line}))
            else:
                # We round up here because the user expects that if he has to consume a little more, the whole UOM unit
                # should be consumed.
                rounding = current_line.product_uom_id.rounding
                line_quantity = float_round(line_quantity, precision_rounding=rounding, rounding_method='UP')
                lines_done.append((current_line, {'target_product': line_product, 'qty': line_quantity, 'product': current_product, 'original_qty': quantity, 'parent_line': parent_line}))

        return boms_done, lines_done
