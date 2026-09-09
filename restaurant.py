import json
import sqlite3
import secrets
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, abort, send_file
from store_database import get_store_connection
from store_controller import get_store

restaurant_bp = Blueprint('restaurant', __name__)

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def enabled(store_id):
    """Return whether the Restaurant add-on is enabled for this store.

    sqlite3.Row does not provide dict.get(), so read the controller
    column explicitly. This is important because the POS status endpoint
    uses this function to decide whether the Restaurant button is shown.
    """
    sid = str(store_id or '').strip().upper()
    if not sid:
        return False

    store = get_store(sid)
    if store is None:
        return False

    try:
        return bool(store['restaurant_mode_enabled'])
    except (KeyError, IndexError):
        return False

def conn(store_id):
    if not enabled(store_id):
        abort(404)
    c = get_store_connection(store_id)
    c.row_factory = sqlite3.Row
    return c

def init_restaurant_db(store_id):
    c = get_store_connection(store_id)
    cur = c.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS restaurant_ingredients (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      purchase_pack TEXT NOT NULL,
      pack_quantity REAL NOT NULL,
      unit TEXT NOT NULL,
      pack_cost REAL NOT NULL,
      base_unit_cost REAL NOT NULL DEFAULT 0,
      stock_quantity REAL NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS restaurant_menu (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      category TEXT NOT NULL DEFAULT 'General',
      selling_price REAL NOT NULL,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS restaurant_categories (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      emoji TEXT NOT NULL,
      display_order INTEGER NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS restaurant_recipe_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      menu_id INTEGER NOT NULL,
      ingredient_id INTEGER NOT NULL,
      quantity REAL NOT NULL,
      FOREIGN KEY(menu_id) REFERENCES restaurant_menu(id) ON DELETE CASCADE,
      FOREIGN KEY(ingredient_id) REFERENCES restaurant_ingredients(id)
    );
    CREATE TABLE IF NOT EXISTS restaurant_orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_number TEXT NOT NULL UNIQUE,
      source TEXT NOT NULL DEFAULT 'POS',
      status TEXT NOT NULL DEFAULT 'PENDING_PAYMENT',
      payment_method TEXT,
      customer_name TEXT,
      total REAL NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      paid_at TEXT,
      completed_at TEXT,
      customer_token TEXT
    );
    CREATE TABLE IF NOT EXISTS restaurant_order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL,
      menu_id INTEGER,
      product_name TEXT NOT NULL,
      quantity REAL NOT NULL,
      unit_price REAL NOT NULL,
      line_total REAL NOT NULL,
      ingredient_cost REAL NOT NULL DEFAULT 0,
      FOREIGN KEY(order_id) REFERENCES restaurant_orders(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS restaurant_expenses (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      amount REAL NOT NULL,
      expense_date TEXT NOT NULL,
      notes TEXT
    );
    CREATE TABLE IF NOT EXISTS restaurant_stock_movements (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ingredient_id INTEGER NOT NULL,
      movement_type TEXT NOT NULL,
      quantity REAL NOT NULL,
      cost REAL NOT NULL DEFAULT 0,
      reference TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY(ingredient_id) REFERENCES restaurant_ingredients(id)
    );
    ''')
    # Every store gets the same built-in restaurant categories. Products are
    # added underneath these categories; existing stores are upgraded here too.
    default_categories = [
        ('Russian', '🌭'),
        ('Burger', '🍔'),
        ('Fish', '🐟'),
        ('Quta', '🥪'),
        ('Chicken', '🍗'),
        ('Chips', '🍟'),
        ('Meals', '🍽️'),
        ('Ribs', '🍖'),
        ('Pork', '🥩'),
        ('Beef', '🥩'),
        ('Pap', '🥣'),
        ('Rice', '🍚'),
        ('Salad', '🥗'),
        ('Ice cream', '🍦'),
    ]
    for order, (name, emoji) in enumerate(default_categories, 1):
        c.execute(
            "INSERT OR IGNORE INTO restaurant_categories(name,emoji,display_order,active) VALUES(?,?,?,1)",
            (name, emoji, order)
        )
        c.execute(
            "UPDATE restaurant_categories SET emoji=?,display_order=?,active=1 WHERE name=?",
            (emoji, order, name)
        )

    try:
        c.execute("ALTER TABLE restaurant_orders ADD COLUMN stock_deducted INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE restaurant_order_items ADD COLUMN ingredient_cost REAL NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE restaurant_orders ADD COLUMN customer_token TEXT")
    except sqlite3.OperationalError:
        pass
    # Give older online orders a private customer token so their status/receipt
    # can be retrieved without exposing the order by numeric database ID.
    rows = c.execute("SELECT id FROM restaurant_orders WHERE source='ONLINE' AND (customer_token IS NULL OR customer_token='')").fetchall()
    for r in rows:
        c.execute("UPDATE restaurant_orders SET customer_token=? WHERE id=?", (secrets.token_urlsafe(24), r['id']))
    c.commit(); c.close()

def rowdicts(rows): return [dict(r) for r in rows]

def ingredient_cost(r):
    return round(float(r['pack_cost']) / float(r['pack_quantity']), 6) if float(r['pack_quantity']) else 0

def menu_cost(c, menu_id):
    rows = c.execute('''SELECT ri.quantity, i.base_unit_cost, i.stock_quantity FROM restaurant_recipe_items ri JOIN restaurant_ingredients i ON i.id=ri.ingredient_id WHERE ri.menu_id=?''',(menu_id,)).fetchall()
    return round(sum(float(r['quantity']) * float(r['base_unit_cost']) for r in rows),2)

def build_menu(c, row):
    d=dict(row); d['ingredient_cost']=menu_cost(c,row['id']); d['gross_profit']=round(float(row['selling_price'])-d['ingredient_cost'],2)
    return d

@restaurant_bp.route('/api/restaurant/status')
def restaurant_status():
    """Return the Restaurant add-on state for the logged-in store.

    The browser must never be able to enable the feature itself; the
    Controller remains the authority. The POS only reads the current state.
    """
    from flask import session

    sid = str(session.get('store_id') or '').strip().upper()

    if not sid:
        return jsonify({
            'success': False,
            'enabled': False,
            'message': 'Store access is required.'
        }), 401

    store = get_store(sid)

    if store is None:
        return jsonify({
            'success': False,
            'enabled': False,
            'message': 'Store not found.'
        }), 404

    return jsonify({
        'success': True,
        'enabled': bool(store['restaurant_mode_enabled'])
    })

@restaurant_bp.route('/restaurant')
def owner_page():
    store_id = request.args.get('store_id') or request.cookies.get('easy_sales_store_id')
    # Browser session is preferred; fallback is passed by POS JS as query string.
    from flask import session
    store_id = str(session.get('store_id') or store_id or '').upper()
    if not enabled(store_id): return ('Restaurant Mode is not enabled for this store.',404)
    init_restaurant_db(store_id)
    return render_template('restaurant.html', store_id=store_id, store=get_store(store_id))

@restaurant_bp.route('/restaurant/kitchen')
def kitchen_page():
    from flask import session
    store_id=str(session.get('store_id') or request.args.get('store_id') or '').upper()
    if not enabled(store_id): return ('Restaurant Mode is not enabled for this store.',404)
    init_restaurant_db(store_id)
    return render_template('restaurant_kitchen.html', store_id=store_id)

@restaurant_bp.route('/r/<store_id>')
def customer_page(store_id):
    store_id=store_id.upper()
    if not enabled(store_id): return ('Restaurant ordering is not available.',404)
    init_restaurant_db(store_id)
    return render_template('restaurant_customer.html', store_id=store_id, store=get_store(store_id))

@restaurant_bp.route('/api/restaurant/bootstrap')
def bootstrap():
    store_id=request.args.get('store_id','').upper()
    init_restaurant_db(store_id)
    c=conn(store_id)
    ingredients=rowdicts(c.execute('SELECT * FROM restaurant_ingredients WHERE active=1 ORDER BY name').fetchall())
    categories=rowdicts(c.execute('SELECT id,name,emoji,display_order FROM restaurant_categories WHERE active=1 ORDER BY display_order').fetchall())
    menus=[build_menu(c,r) for r in c.execute('SELECT * FROM restaurant_menu WHERE active=1 ORDER BY category,name').fetchall()]
    for i in ingredients: i['base_unit_cost']=round(float(i['pack_cost'])/float(i['pack_quantity']),6) if i['pack_quantity'] else 0
    c.close(); return jsonify({'success':True,'ingredients':ingredients,'categories':categories,'menus':menus})

@restaurant_bp.route('/api/restaurant/ingredients',methods=['POST'])
def add_ingredient():
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper()
    try:
        pack_qty=float(d['pack_quantity']); pack_cost=float(d['pack_cost']); stock_packs=float(d.get('stock_packs',0))
        if pack_qty<=0 or pack_cost<0 or stock_packs<0: raise ValueError
        unit=str(d.get('unit') or 'each').strip(); name=str(d.get('name') or '').strip(); pack=str(d.get('purchase_pack') or 'pack').strip()
        if not name: raise ValueError
        c=conn(store_id); t=now(); unit_cost=pack_cost/pack_qty
        cur=c.execute('INSERT INTO restaurant_ingredients(name,purchase_pack,pack_quantity,unit,pack_cost,base_unit_cost,stock_quantity,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(name,pack,pack_qty,unit,pack_cost,unit_cost,stock_packs*pack_qty,t,t))
        iid=cur.lastrowid
        if stock_packs: c.execute('INSERT INTO restaurant_stock_movements(ingredient_id,movement_type,quantity,cost,reference,created_at) VALUES(?,?,?,?,?,?)',(iid,'PURCHASE',stock_packs*pack_qty,pack_cost,'Initial stock',t))
        c.commit(); c.close(); return jsonify({'success':True,'id':iid})
    except Exception: return jsonify({'success':False,'message':'Enter valid ingredient details.'}),400

@restaurant_bp.route('/api/restaurant/ingredients/<int:iid>/purchase',methods=['POST'])
def purchase_ingredient(iid):
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper()
    try:
        packs=float(d.get('packs',0)); price=float(d.get('pack_cost',0));
        if packs<=0 or price<0: raise ValueError
        c=conn(store_id); r=c.execute('SELECT * FROM restaurant_ingredients WHERE id=? AND active=1',(iid,)).fetchone()
        if not r: raise ValueError('Ingredient not found.')
        qty=packs*float(r['pack_quantity']); unit_cost=price/float(r['pack_quantity']) if r['pack_quantity'] else 0
        newcost=unit_cost
        c.execute('UPDATE restaurant_ingredients SET pack_cost=?,base_unit_cost=?,stock_quantity=stock_quantity+?,updated_at=? WHERE id=?',(price,newcost,qty,now(),iid))
        c.execute('INSERT INTO restaurant_stock_movements(ingredient_id,movement_type,quantity,cost,reference,created_at) VALUES(?,?,?,?,?,?)',(iid,'PURCHASE',qty,price,f'{packs:g} {r["purchase_pack"]}',now()))
        c.commit(); c.close(); return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'message':str(e)}),400

@restaurant_bp.route('/api/restaurant/menu',methods=['POST'])
def add_menu():
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper()
    try:
        name=str(d.get('name') or '').strip(); cat=str(d.get('category') or 'General').strip(); price=float(d.get('selling_price',0))
        if not name or price<0: raise ValueError
        c=conn(store_id); t=now(); cur=c.execute('INSERT INTO restaurant_menu(name,category,selling_price,created_at,updated_at) VALUES(?,?,?,?,?)',(name,cat,price,t,t)); mid=cur.lastrowid
        for x in d.get('recipe',[]):
            c.execute('INSERT INTO restaurant_recipe_items(menu_id,ingredient_id,quantity) VALUES(?,?,?)',(mid,int(x['ingredient_id']),float(x['quantity'])))
        c.commit(); c.close(); return jsonify({'success':True,'id':mid})
    except Exception: return jsonify({'success':False,'message':'Enter valid menu details and recipe quantities.'}),400

@restaurant_bp.route('/api/restaurant/menu/<int:mid>',methods=['PUT'])
def update_menu(mid):
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper()
    try:
        c=conn(store_id); name=str(d.get('name') or '').strip(); cat=str(d.get('category') or 'General').strip(); price=float(d.get('selling_price',0))
        if not name or price<0: raise ValueError
        c.execute('UPDATE restaurant_menu SET name=?,category=?,selling_price=?,updated_at=? WHERE id=?',(name,cat,price,now(),mid)); c.execute('DELETE FROM restaurant_recipe_items WHERE menu_id=?',(mid,))
        for x in d.get('recipe',[]): c.execute('INSERT INTO restaurant_recipe_items(menu_id,ingredient_id,quantity) VALUES(?,?,?)',(mid,int(x['ingredient_id']),float(x['quantity'])))
        c.commit(); c.close(); return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'message':str(e)}),400

def consume_order_stock(c, order_id):
    order = c.execute('SELECT * FROM restaurant_orders WHERE id=?', (order_id,)).fetchone()
    if not order or int(order['stock_deducted'] or 0): return
    items = c.execute('SELECT * FROM restaurant_order_items WHERE order_id=?', (order_id,)).fetchall()
    for item in items:
        if not item['menu_id']: continue
        recipe = c.execute('SELECT ingredient_id, quantity FROM restaurant_recipe_items WHERE menu_id=?', (item['menu_id'],)).fetchall()
        for r in recipe:
            qty=float(r['quantity'])*float(item['quantity'])
            ing=c.execute('SELECT stock_quantity FROM restaurant_ingredients WHERE id=?', (r['ingredient_id'],)).fetchone()
            if not ing or float(ing['stock_quantity']) < qty:
                raise ValueError('Not enough ingredient stock for '+str(item['product_name']))
            c.execute('UPDATE restaurant_ingredients SET stock_quantity=stock_quantity-?,updated_at=? WHERE id=?',(qty,now(),r['ingredient_id']))
            c.execute('INSERT INTO restaurant_stock_movements(ingredient_id,movement_type,quantity,cost,reference,created_at) VALUES(?,?,?,?,?,?)',(r['ingredient_id'],'CONSUMPTION',-qty,float(ing['stock_quantity'])*0,'Order '+str(order['order_number']),now()))
    c.execute('UPDATE restaurant_orders SET stock_deducted=1 WHERE id=?',(order_id,))

@restaurant_bp.route('/api/restaurant/orders',methods=['GET','POST'])
def orders():
    store_id=str((request.get_json(silent=True) or {}).get('store_id') if request.method=='POST' else request.args.get('store_id') or '').upper()
    c=conn(store_id); init_restaurant_db(store_id)
    if request.method=='GET':
        rows=c.execute('SELECT * FROM restaurant_orders ORDER BY id DESC LIMIT 100').fetchall(); out=[]
        for r in rows:
            d=dict(r); d['items']=rowdicts(c.execute('SELECT * FROM restaurant_order_items WHERE order_id=?',(r['id'],)).fetchall()); out.append(d)
        c.close(); return jsonify({'success':True,'orders':out})
    d=request.get_json(silent=True) or {}; items=d.get('items') or []; source=str(d.get('source') or 'POS'); customer=str(d.get('customer_name') or '').strip()
    try:
        if not items: raise ValueError('No items.')
        total=0; normalized=[]
        for x in items:
            mid=int(x['menu_id']); qty=float(x['quantity']); r=c.execute('SELECT * FROM restaurant_menu WHERE id=? AND active=1',(mid,)).fetchone()
            if not r or qty<=0: raise ValueError('Invalid menu item.')
            lt=float(r['selling_price'])*qty; total+=lt; normalized.append((mid,r['name'],qty,float(r['selling_price']),lt,menu_cost(c,mid)))
        t=now(); order_no=f'R{datetime.now().strftime("%y%m%d")}-{int(datetime.now().timestamp())%100000:05d}'
        customer_token = secrets.token_urlsafe(24) if source.upper() == 'ONLINE' else None
        cur=c.execute('INSERT INTO restaurant_orders(order_number,source,status,customer_name,total,created_at,customer_token) VALUES(?,?,?,?,?,?,?)',(order_no,source,'PENDING_PAYMENT',customer,total,t,customer_token)); oid=cur.lastrowid
        for x in normalized: c.execute('INSERT INTO restaurant_order_items(order_id,menu_id,product_name,quantity,unit_price,line_total,ingredient_cost) VALUES(?,?,?,?,?,?,?)',(oid,*x))
        c.commit(); c.close(); return jsonify({'success':True,'order_number':order_no,'order_id':oid,'total':total,'status':'PENDING_PAYMENT','customer_token':customer_token})
    except Exception as e: c.close(); return jsonify({'success':False,'message':str(e)}),400

@restaurant_bp.route('/api/restaurant/online-order/status')
def online_order_status():
    store_id=str(request.args.get('store_id') or '').upper()
    token=str(request.args.get('token') or '').strip()
    if not store_id or not token:
        return jsonify({'success':False,'message':'Order tracking information is required.'}),400
    c=conn(store_id)
    order=c.execute('SELECT id,order_number,status,customer_name,total,created_at FROM restaurant_orders WHERE source="ONLINE" AND customer_token=?',(token,)).fetchone()
    if not order:
        c.close(); return jsonify({'success':False,'message':'Online order not found.'}),404
    messages={
        'PENDING_PAYMENT':'Order received. Please pay at the cashier.',
        'PAID':'Payment received. Your order is waiting for the kitchen.',
        'ACCEPTED':'Your order has been accepted by the restaurant.',
        'PREPARING':'Your food is being prepared.',
        'READY':'🎉 Your food is ready! Please collect your order.',
        'COLLECTED':'Your order has been collected. Thank you!',
        'CANCELLED':'Your order was cancelled. Please speak to the restaurant.'
    }
    c.close()
    return jsonify({'success':True,'order':dict(order),'message':messages.get(order['status'],'Your order is being processed.')})

@restaurant_bp.route('/api/restaurant/online-order/receipt')
def online_order_receipt():
    store_id=str(request.args.get('store_id') or '').upper()
    token=str(request.args.get('token') or '').strip()
    if not store_id or not token:
        return jsonify({'success':False,'message':'Receipt information is required.'}),400
    c=conn(store_id)
    order=c.execute('SELECT * FROM restaurant_orders WHERE source="ONLINE" AND customer_token=?',(token,)).fetchone()
    if not order:
        c.close(); return jsonify({'success':False,'message':'Online order not found.'}),404
    items=c.execute('SELECT product_name,quantity,unit_price,line_total FROM restaurant_order_items WHERE order_id=? ORDER BY id',(order['id'],)).fetchall()
    store=get_store(store_id)
    c.close()

    # Generate a compact PDF receipt on demand. The customer page automatically
    # downloads it after placing an online order. Mobile browsers may still ask
    # the user to confirm the download depending on device/browser settings.
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    buf=BytesIO()
    pdf=canvas.Canvas(buf,pagesize=A5)
    width,height=A5
    x=15*mm; y=height-15*mm
    name=(store['store_name'] if store else 'Easy_Sales Restaurant')
    pdf.setFont('Helvetica-Bold',15); pdf.drawString(x,y,str(name)[:55]); y-=8*mm
    pdf.setFont('Helvetica',9); pdf.drawString(x,y,'ONLINE ORDER RECEIPT'); y-=6*mm
    pdf.drawString(x,y,'Order: '+str(order['order_number'])); y-=5*mm
    pdf.drawString(x,y,'Date: '+str(order['created_at'])); y-=5*mm
    if order['customer_name']:
        pdf.drawString(x,y,'Customer: '+str(order['customer_name'])[:45]); y-=7*mm
    pdf.line(x,y,width-x,y); y-=6*mm
    for item in items:
        label=f"{item['product_name']} x {item['quantity']:g}"
        pdf.drawString(x,y,label[:45]); pdf.drawRightString(width-x,y,f"R{float(item['line_total']):.2f}"); y-=5*mm
        if y<25*mm:
            pdf.showPage(); y=height-15*mm; pdf.setFont('Helvetica',9)
    y-=2*mm; pdf.line(x,y,width-x,y); y-=6*mm
    pdf.setFont('Helvetica-Bold',12); pdf.drawString(x,y,'TOTAL'); pdf.drawRightString(width-x,y,f"R{float(order['total']):.2f}"); y-=8*mm
    pdf.setFont('Helvetica',9); pdf.drawString(x,y,'Status: '+str(order['status'])); y-=7*mm
    pdf.drawString(x,y,'Thank you for ordering with Easy_Sales.')
    pdf.save(); buf.seek(0)
    return send_file(buf,mimetype='application/pdf',as_attachment=True,download_name=f"Easy_Sales_{order['order_number']}.pdf")

@restaurant_bp.route('/api/restaurant/orders/<int:oid>/pay',methods=['POST'])
def pay_order(oid):
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper(); method=str(d.get('payment_method') or 'CASH').upper(); c=conn(store_id); r=c.execute('SELECT * FROM restaurant_orders WHERE id=?',(oid,)).fetchone()
    if not r: c.close(); return jsonify({'success':False,'message':'Order not found.'}),404
    try:
        consume_order_stock(c, oid)
        c.execute("UPDATE restaurant_orders SET status='PAID',payment_method=?,paid_at=? WHERE id=?",(method,now(),oid)); c.commit(); c.close(); return jsonify({'success':True})
    except Exception as e:
        c.rollback(); c.close(); return jsonify({'success':False,'message':str(e)}),400

@restaurant_bp.route('/api/restaurant/orders/<int:oid>/status',methods=['POST'])
def order_status(oid):
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper(); status=str(d.get('status') or '').upper(); allowed={'ACCEPTED','PREPARING','READY','COLLECTED','CANCELLED'}
    if status not in allowed: return jsonify({'success':False,'message':'Invalid status.'}),400
    c=conn(store_id); r=c.execute('SELECT * FROM restaurant_orders WHERE id=?',(oid,)).fetchone()
    if not r: c.close(); return jsonify({'success':False,'message':'Order not found.'}),404
    c.execute('UPDATE restaurant_orders SET status=?,completed_at=CASE WHEN ? IN ("COLLECTED","CANCELLED") THEN ? ELSE completed_at END WHERE id=?',(status,status,now(),oid)); c.commit(); c.close(); return jsonify({'success':True})

@restaurant_bp.route('/api/restaurant/expenses',methods=['POST'])
def expense():
    d=request.get_json(silent=True) or {}; store_id=str(d.get('store_id','')).upper(); name=str(d.get('name') or '').strip(); amount=float(d.get('amount',0)); date=str(d.get('expense_date') or now()[:10]);
    if not name or amount<0: return jsonify({'success':False,'message':'Invalid expense.'}),400
    c=conn(store_id); c.execute('INSERT INTO restaurant_expenses(name,amount,expense_date,notes) VALUES(?,?,?,?)',(name,amount,date,str(d.get('notes') or ''))); c.commit(); c.close(); return jsonify({'success':True})

@restaurant_bp.route('/api/restaurant/report')
def report():
    store_id=request.args.get('store_id','').upper(); c=conn(store_id)
    sales=c.execute("SELECT COALESCE(SUM(total),0) v, COUNT(*) n FROM restaurant_orders WHERE status IN ('PAID','ACCEPTED','PREPARING','READY','COLLECTED')").fetchone()
    itemrows=c.execute("SELECT product_name,SUM(quantity) qty,SUM(line_total) revenue FROM restaurant_order_items oi JOIN restaurant_orders o ON o.id=oi.order_id WHERE o.status NOT IN ('CANCELLED','PENDING_PAYMENT') GROUP BY product_name ORDER BY qty DESC").fetchall()
    top=[]
    for r in itemrows:
        midrow=c.execute('SELECT menu_id FROM restaurant_order_items oi JOIN restaurant_orders o ON o.id=oi.order_id WHERE oi.product_name=? LIMIT 1',(r['product_name'],)).fetchone(); costrow=c.execute("SELECT COALESCE(SUM(ingredient_cost*quantity),0) v FROM restaurant_order_items oi2 JOIN restaurant_orders o2 ON o2.id=oi2.order_id WHERE oi2.product_name=? AND o2.status NOT IN ('CANCELLED','PENDING_PAYMENT')", (r['product_name'],)).fetchone(); estcost=float(costrow['v'] or 0)
        top.append({'product_name':r['product_name'],'quantity_sold':r['qty'],'revenue':round(r['revenue'],2),'estimated_cost':round(estcost,2),'estimated_profit':round((r['revenue']-estcost),2)})
    expenses=c.execute('SELECT COALESCE(SUM(amount),0) v FROM restaurant_expenses').fetchone()['v']
    c.close(); return jsonify({'success':True,'revenue':round(sales['v'],2),'orders':sales['n'],'expenses':round(expenses,2),'items':top})
