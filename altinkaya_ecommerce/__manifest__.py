# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Altinkaya E-commerce Extensions",
    "summary": "Product and sale e-commerce fields",
    "description": "- Websitesinde yayınlanan kategorileri arama ve film şeridi kısmında filtreler.\n"
    "- Ürünlerin websitesinde yayınlanıp yayınlanmayacağını belirleme.\n",
    "development_status": "Beta",
    "version": "16.0.1.0.1",
    "author": "Yiğit Budak",
    "license": "AGPL-3",
    "website": "https://github.com/yibudak",
    "category": "Extensions",
    "depends": ["product", "website_sale", "website_sale_comparison"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_attribute_view.xml",
        "views/product_template_view.xml",
        "views/product_product_view.xml",
        "views/res_partner_view.xml",
        "views/product_public_category_view.xml",
        "views/product_category_view.xml",
        # TEMPLATES
        "templates/product_attachments_table.xml",
        "templates/product_features_table.xml",
        "templates/product_category_filmstrip.xml",
        "templates/product_attributes_filter.xml",
        "templates/product_template_hide_price.xml",
        "templates/product_html_description.xml",
        # SNIPPETS
        "views/snippets/s_dynamic_category_table.xml",
    ],
    "assets": {
        "website.assets_wysiwyg": [
            "altinkaya_ecommerce/static/src/snippets/s_dynamic_category_table/options.js",
        ],
    },
    "installable": True,
}
