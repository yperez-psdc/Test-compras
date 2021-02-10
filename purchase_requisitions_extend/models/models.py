# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = "res.company"

    is_purchase_validation_required = fields.Boolean(string="Purchase validation Required ?", default=False)
    purchase_user_amount_min = fields.Float(string="Purchase User Amount")
    purchase_user_amount_max = fields.Float(string="Purchase User Amount")
    
    department_manager_amount_min= fields.Float(string="Department Manager Amount")
    department_manager_amount_max= fields.Float(string="Department Manager Amount")

    director_amount_min= fields.Float(string="Director Amount")
    director_amount_max= fields.Float(string="Director Amount")

    cfo_amount_min= fields.Float(string="CFO Amount")
    cfo_amount_max= fields.Float(string="CFO Amount")

    ceo_amount_min= fields.Float(string="Department Manager Amount")




class RequisitionLine(models.Model):
    _inherit = "requisition.line"

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

class MaterialPurchaseRequisition(models.Model):
    _inherit = "material.purchase.requisition"
    

    def _get_default_employee_id(self):
        logged_in_user = self.env.user
        logged_in_employee = self.env['hr.employee'].sudo().search([('user_id', '=', logged_in_user.id)], limit=1)
        if logged_in_employee:
            return logged_in_employee.id


    @api.onchange('requisition_responsible_id')
    def _get_default_approver(self):
        user_ids = self.env['res.users'].search([])
        user_eligible = []
        for user in user_ids:
            if user.has_group('bi_material_purchase_requisitions.group_requisition_department_manager'):
                user_eligible.append(user.id)
        return {'domain':{'requisition_responsible_id':[('id','in',user_eligible)]}}
    

    @api.onchange('employee_id')
    def get_department(self):
        self.department_id = self.employee_id.department_id.id

    employee_id = fields.Many2one('hr.employee',string="Employee",required=True,default=_get_default_employee_id)
    department_id = fields.Many2one('hr.department',string="Department",required=True)
    requisition_responsible_id  = fields.Many2one('res.users',string="Requisition Responsible")




    def create_picking_po(self):
        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']
        for requisition in self:
            for line in requisition.requisition_line_ids:
                if line.requisition_action == 'purchase_order':
                    for vendor in line.vendor_id:
                        pur_order = purchase_order_obj.search([('requisition_po_id','=',requisition.id),('partner_id','=',vendor.id)])
                        if pur_order:
                            po_line_vals = {
                                'product_id' : line.product_id.id,
                                'product_qty': line.qty,
                                'name' : line.description,
                                'price_unit' : line.product_id.list_price,
                                'date_planned' : datetime.now(),
                                'product_uom' : line.uom_id.id,
                                'order_id' : pur_order.id,
                            }
                            if line.account_analytic_id:
                                po_line_vals['account_analytic_id'] = line.account_analytic_id.id
                            purchase_order_line = purchase_order_line_obj.create(po_line_vals)
                        else:
                            vals = {
                                'partner_id' : vendor.id,
                                'date_order' : datetime.now(),
                                'requisition_po_id' : requisition.id,
                                'origin': requisition.sequence,
                                'state' : 'draft',
                                'picking_type_id' : requisition.picking_type_id.id                                
                            }
                            purchase_order = purchase_order_obj.create(vals)
                            po_line_vals = {
                                'product_id' : line.product_id.id,
                                'product_qty': line.qty,
                                'name' : line.description,
                                'price_unit' : line.product_id.list_price,
                                'date_planned' : datetime.now(),
                                'product_uom' : line.uom_id.id,
                                'order_id' : purchase_order.id,
                            }
                            if line.account_analytic_id:
                                po_line_vals['account_analytic_id'] = line.account_analytic_id.id
                            purchase_order_line = purchase_order_line_obj.create(po_line_vals)
                else:
                    stock_picking_obj = self.env['stock.picking']
                    stock_move_obj = self.env['stock.move']
                    stock_picking_type_obj = self.env['stock.picking.type']
                    picking_type_id = False

                    if not requisition.use_manual_locations:
                        picking_type_id = requisition.internal_picking_id
                    else:
                        picking_type_id = stock_picking_type_obj.search([('code','=','internal'),('company_id','=', requisition.company_id.id or False)], order="id desc", limit=1)

                        if not picking_type_id :
                            picking_type_id = requisition.internal_picking_id

                    if line.vendor_id:                    
                        for vendor in line.vendor_id:
                        
                            pur_order = stock_picking_obj.search([('requisition_picking_id','=',requisition.id),('partner_id','=',vendor.id)])
                            
                            if pur_order:
                                if requisition.use_manual_locations:
                                    pic_line_val = {
                                        'name': line.product_id.name,
                                        'product_id' : line.product_id.id,
                                        'product_uom_qty' : line.qty,
                                        'picking_id' : picking_type_id.id,
                                        'product_uom' : line.uom_id.id,
                                        'location_id': requisition.source_location_id.id,
                                        'location_dest_id' : requisition.destination_location_id.id,
                                    }
                                else:
                                    pic_line_val = {
                                        'name': line.product_id.name,
                                        'product_id' : line.product_id.id,
                                        'product_uom_qty' : line.qty,
                                        'picking_id' : picking_type_id.id,
                                        'product_uom' : line.uom_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                    }                                    


                                stock_move = stock_move_obj.create(pic_line_val)
                            else:
                                if requisition.use_manual_locations:
                                    val = {
                                        'partner_id' : vendor.id,
                                        'location_id'  : requisition.source_location_id.id,
                                        'location_dest_id' : requisition.destination_location_id.id,
                                        'picking_type_id' : picking_type_id.id,
                                        'company_id': requisition.env.user.company_id.id,
                                        'requisition_picking_id' : requisition.id,
                                        'origin':requisition.sequence,
                                        'location_id': requisition.source_location_id.id,
                                        'location_dest_id' : requisition.destination_location_id.id,
                                    }

                                    
                                else:


                                    val = {
                                        'partner_id' : vendor.id,
                                        'location_id'  : picking_type_id.default_location_src_id.id,
                                        'location_dest_id' :picking_type_id.default_location_src_id.id,
                                        'picking_type_id' : picking_type_id.id,
                                        'company_id': requisition.env.user.company_id.id,
                                        'requisition_picking_id' : requisition.id,
                                        'location_id': picking_type_id.default_location_src_id.id or vendor.property_stock_supplier.id,
                                        'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                        'origin':requisition.sequence
                                    }   
                                                                    

                                stock_picking = stock_picking_obj.create(val)
                                if requisition.use_manual_locations:
                                    pic_line_val = {
                                                    'partner_id' : vendor.id,
                                                    'name': line.product_id.name,
                                                    'product_id' : line.product_id.id,
                                                    'product_uom_qty' : line.qty,
                                                    'product_uom' : line.uom_id.id,
                                                    'location_id': requisition.source_location_id.id,
                                                    'location_dest_id' : requisition.destination_location_id.id,
                                                    'picking_id' : stock_picking.id,
                                                    'origin': requisition.sequence

                                    }
                                else:
                                    pic_line_val = {
                                                    'partner_id' : vendor.id,
                                                    'name': line.product_id.name,
                                                    'product_id' : line.product_id.id,
                                                    'product_uom_qty' : line.qty,
                                                    'product_uom' : line.uom_id.id,
                                                    'location_id': picking_type_id.default_location_src_id.id or vendor.property_stock_supplier.id,
                                                    'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                                    'picking_id' : stock_picking.id,
                                                    'origin': requisition.sequence

                                    }                                    
                                stock_move = stock_move_obj.create(pic_line_val)
                    else:
                        pur_order = stock_picking_obj.search([('requisition_picking_id','=',requisition.id)])                     

                        if pur_order:
                            if requisition.use_manual_locations:
                                pic_line_val = {
                                    'name': line.product_id.name,
                                    'product_id' : line.product_id.id,
                                    'product_uom_qty' : line.qty,
                                    'picking_id' : stock_picking.id,
                                    'product_uom' : line.uom_id.id,
                                    'location_id': requisition.source_location_id.id,
                                    'location_dest_id' : requisition.destination_location_id.id,
                                }
                            else:
                                location  = self.env['stock.location'].search([('usage','=','supplier')],limit=1)
                                pic_line_val = {
                                    'name': line.product_id.name,
                                    'product_id' : line.product_id.id,
                                    'product_uom_qty' : line.qty,
                                    'picking_id' : stock_picking.id,
                                    'product_uom' : line.uom_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id or location.id,
                                    'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                }                                

                            stock_move = stock_move_obj.create(pic_line_val)
                        else:
                            if requisition.use_manual_locations:


                                val = {
                                    'location_id'  : requisition.source_location_id.id,
                                    'location_dest_id' : requisition.destination_location_id.id,
                                    'picking_type_id' : picking_type_id.id,
                                    'company_id': requisition.env.user.company_id.id,
                                    'requisition_picking_id' : requisition.id,
                                    'origin':requisition.sequence,
                                    'location_id': requisition.source_location_id.id,
                                    'location_dest_id' : requisition.destination_location_id.id,
                                }
                            else:

                                location  = self.env['stock.location'].search([('usage','=','supplier')],limit=1)
                                val = {
                                    'location_id'  : picking_type_id.default_location_src_id.id,
                                    'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                    'picking_type_id' : picking_type_id.id,
                                    'company_id': requisition.env.user.company_id.id,
                                    'requisition_picking_id' : requisition.id,
                                    'origin':requisition.sequence,
                                    'location_id': picking_type_id.default_location_src_id.id or location.id,
                                    'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                }                                


                            stock_picking = stock_picking_obj.create(val)
                            if requisition.use_manual_locations:
                                pic_line_val = {
                                                'name': line.product_id.name,
                                                'product_id' : line.product_id.id,
                                                'product_uom_qty' : line.qty,
                                                'product_uom' : line.uom_id.id,
                                                'location_id': requisition.source_location_id.id,
                                                'location_dest_id' : requisition.destination_location_id.id,
                                                'picking_id' : stock_picking.id,
                                                'origin': requisition.sequence

                                }
                            else:
                                location  = self.env['stock.location'].search([('usage','=','supplier')],limit=1)
                                pic_line_val = {
                                                'name': line.product_id.name,
                                                'product_id' : line.product_id.id,
                                                'product_uom_qty' : line.qty,
                                                'product_uom' : line.uom_id.id,
                                                'location_id': picking_type_id.default_location_src_id.id or location.id,
                                                'location_dest_id' : picking_type_id.default_location_dest_id.id,
                                                'picking_id' : stock_picking.id,
                                                'origin': requisition.sequence

                                }
                            stock_move = stock_move_obj.create(pic_line_val)
            requisition.write({
                'state':'po_created',
            })               


class PurchaseOrder(models.Model):      
    _inherit = 'purchase.order'   

    def calculate_validation_purchasing_user(self):
        if self:
            for rec in self:
                if rec.validation_purchasing_user ==True:
                    rec.compute_validation_purchasing_user = True
                elif rec.validation_level_required in ['one', 'two', 'three','four', 'five', False] :
                    rec.compute_validation_purchasing_user =True
                elif rec.state in ["draft","sent","to_approve"]:
                    rec.compute_validation_purchasing_user =False

    def calculate_validation_purchasing_manager(self):
        if self:
            for rec in self:
                if rec.validation_purchasing_manager ==True:
                    rec.compute_validation_purchasing_manager = True
                elif rec.validation_level_required in ['no', 'one', False]:
                    rec.compute_validation_purchasing_manager =True
                elif rec.state in ["draft","sent","to_approve"]: 
                    rec.compute_validation_purchasing_manager = False


    def calculate_validation_department_manager(self):
        if self:
            for rec in self:
                if rec.validation_department_manager ==True:
                    rec.compute_validation_department_manager = True
                elif rec.validation_level_required in ['no', 'one', False]:
                    rec.compute_validation_department_manager =True
                elif rec.state in ["draft","sent","to_approve"]:
                    rec.compute_validation_department_manager =False


    def calculate_validation_director(self):
        if self:
            for rec in self:
                if rec.validation_director ==True:
                    rec.compute_validation_director = True
                elif rec.validation_level_required in ['no', 'one', 'two', False]:
                    rec.compute_validation_director =True
                elif rec.state in ["draft","sent","to_approve"]:
                    rec.compute_validation_director =False

    def calculate_validation_cfo_or_coo(self):
        if self:
            for rec in self:
                if rec.validation_cfo_or_coo ==True:
                    rec.compute_validation_cfo_or_coo = True
                elif rec.validation_level_required in ['no', 'one', 'two', 'three', False]:
                    rec.compute_validation_cfo_or_coo =True
                elif rec.state in ["draft","sent","to_approve"]:
                    rec.compute_validation_cfo_or_coo =False


    def calculate_validation_ceo(self):
        if self:
            for rec in self:
                if rec.validation_ceo ==True:
                    rec.compute_validation_ceo = True
                elif rec.validation_level_required in ['no', 'one', 'two', 'three', 'four', False]:
                    rec.compute_validation_ceo =True
                elif rec.state in ["draft","sent","to_approve"]:
                    rec.compute_validation_ceo =False


    compute_validation_purchasing_user = fields.Boolean(string="Purchasing User", compute='calculate_validation_purchasing_user')
    compute_validation_purchasing_manager = fields.Boolean(string="Purchasing Manager", compute='calculate_validation_purchasing_manager')
    compute_validation_department_manager = fields.Boolean(string="Department Manager", compute='calculate_validation_department_manager')
    compute_validation_director = fields.Boolean(string="Director", compute='calculate_validation_director')
    compute_validation_cfo_or_coo = fields.Boolean(string="CFO or COO", compute='calculate_validation_cfo_or_coo')
    compute_validation_ceo = fields.Boolean(string="CEO", compute='calculate_validation_ceo')


    validation_purchasing_user = fields.Boolean(string="Purchasing User", default=False)
    validation_purchasing_manager = fields.Boolean(string="Purchasing Manager", default=False)
    validation_department_manager = fields.Boolean(string="Department Manager", default=False)
    validation_director = fields.Boolean(string="Director", default=False)
    validation_cfo_or_coo = fields.Boolean(string="CFO or COO", default=False)
    validation_ceo = fields.Boolean(string="CEO", default=False)

    def _compute_validation_level_required(self):
        for rec in self:
            purchase_user_amount_min = self.env.company.purchase_user_amount_min
            purchase_user_amount_max = self.env.company.purchase_user_amount_max
            department_manager_amount_min = self.env.company.department_manager_amount_min
            department_manager_amount_max = self.env.company.department_manager_amount_max
            director_amount_min = self.env.company.director_amount_min
            director_amount_max = self.env.company.director_amount_max
            cfo_amount_min = self.env.company.cfo_amount_min
            cfo_amount_max = self.env.company.cfo_amount_max
            ceo_amount_min = self.env.company.ceo_amount_min

            if rec.company_id.is_purchase_validation_required:
                if rec.amount_total >purchase_user_amount_min and rec.amount_total <= purchase_user_amount_max:
                    rec.validation_level_required = 'no'
                elif rec.amount_total > department_manager_amount_min and rec.amount_total <=department_manager_amount_max:
                    rec.validation_level_required = 'two'
                elif rec.amount_total > director_amount_min and rec.amount_total <= director_amount_max:
                    rec.validation_level_required = 'three'
                elif rec.amount_total > cfo_amount_min and rec.amount_total <=cfo_amount_max:
                    rec.validation_level_required = 'four'
                elif rec.amount_total > ceo_amount_min:
                    rec.validation_level_required = 'five'
            else:
                rec.validation_level_required = 'no'


    validation_level_required = fields.Selection([
        ('no', 'No'),
        ('one', 'one'),
        ('two', 'two'),
        ('three', 'three'),
        ('four', 'four'),
        ('five', 'five'),
        ],string = "Validation Level Required", compute='_compute_validation_level_required')


    def button_confirm(self):
        for rec in self:
            if rec.validation_level_required == 'no':
                if rec.validation_purchasing_user ==True:
                    super(PurchaseOrder, self).button_confirm()
                else:
                    if rec.validation_purchasing_user ==False:
                        raise ValidationError(_("Purchasing User Approval Required"))

            elif rec.validation_level_required == 'two':
                if rec.validation_purchasing_manager ==True and rec.validation_department_manager==True:
                    super(PurchaseOrder, self).button_confirm()
                else:
                    if rec.validation_purchasing_manager==False:
                        raise ValidationError(_("Purchasing Manager Approval Required"))
                    elif rec.validation_department_manager==False:
                        raise ValidationError(_("Department Manager Approval Required"))
                        
            elif rec.validation_level_required == 'three':
                if rec.validation_purchasing_manager ==True and rec.validation_department_manager==True and rec.validation_director==True :
                    super(PurchaseOrder, self).button_confirm()
                else:
                    if rec.validation_purchasing_manager==False:
                        raise ValidationError(_("Purchasing Manager Approval Required"))
                    elif rec.validation_department_manager==False:
                        raise ValidationError(_("Department Manager Approval Required"))
                    elif rec.validation_director==False:
                        raise ValidationError(_("Director Approval Required"))
            elif rec.validation_level_required == 'four':
                if rec.validation_purchasing_manager ==True and rec.validation_department_manager==True and rec.validation_director==True and rec.validation_cfo_or_coo==True:
                    super(PurchaseOrder, self).button_confirm()
                else:
                    if rec.validation_purchasing_manager==False:
                        raise ValidationError(_("Purchasing Manager Approval Required"))
                    elif rec.validation_department_manager==False:
                        raise ValidationError(_("Department Manager Approval Required"))
                    elif rec.validation_director==False:
                        raise ValidationError(_("Director Approval Required"))
                    elif rec.validation_cfo_or_coo==False:
                        raise ValidationError(_("CFO/COO Approval Required"))
                        
            elif rec.validation_level_required == 'five':
                if rec.validation_purchasing_manager ==True and rec.validation_department_manager==True and rec.validation_director==True and rec.validation_cfo_or_coo==True and rec.validation_ceo==True:
                    super(PurchaseOrder, self).button_confirm()
                else:
                    if rec.validation_purchasing_manager==False:
                        raise ValidationError(_("Purchasing Manager Approval Required"))
                    elif rec.validation_department_manager==False:
                        raise ValidationError(_("Department Manager Approval Required"))
                    elif rec.validation_director==False:
                        raise ValidationError(_("Director Approval Required"))
                    elif rec.validation_cfo_or_coo==False:
                        raise ValidationError(_("CFO/COO Approval Required"))
                    elif rec.validation_ceo==False:
                        raise ValidationError(_("CEO Approval Required"))

    def button_validation_purchasing_user(self):
        self.validation_purchasing_user = True

    def button_validation_purchasing_manager(self):
        self.validation_purchasing_manager = True

    def button_validation_department_manager(self):
        self.validation_department_manager = True

    def button_validation_director(self):
        self.validation_director = True

    def button_validation_cfo_or_coo(self):
        self.validation_cfo_or_coo = True

    def button_validation_ceo(self):
        self.validation_ceo = True