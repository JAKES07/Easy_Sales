import json
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, abort
from store_database import get_store_connection
from store_controller import get_store

restaurant_bp = Blueprint('restaurant', __name__)

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def enabled(store_id):
    store = get_store(store_id)
    return bool(store and store.get('restaurant_mode_enabled'))

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
      completed_at TEXT
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
    try:
        c.execute("ALTER TABLE restaurant_orders ADD COLUMN stock_deducted INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE restaurant_order_items ADD COLUMN ingredient_cost REAL NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
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
    from flask import session
    sid=str(session.get('store_id') or request.args.get('store_id') or '').upper()
    return jsonify({'success':True,'enabled':bool(sid and enabled(sid))})

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
    store_id=request.args.get('store_id','').upper(); c=conn(store_id); init_restaurant_db(store_id)
    ingredients=rowdicts(c.execute('SELECT * FROM restaurant_ingredients WHERE active=1 ORDER BY name').fetchall())
    menus=[build_menu(c,r) for r in c.execute('SELECT * FROM restaurant_menu WHERE active=1 ORDER BY category,name').fetchall()]
    for i in ingredients: i['base_unit_cost']=round(float(i['pack_cost'])/float(i['pack_quantity']),6) if i['pack_quantity'] else 0
    c.close(); return jsonify({'success':True,'ingredients':ingredients,'menus':menus})

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
        cur=c.execute('INSERT INTO restaurant_orders(order_number,source,status,customer_name,total,created_at) VALUES(?,?,?,?,?,?)',(order_no,source,'PENDING_PAYMENT',customer,total,t)); oid=cur.lastrowid
        for x in normalized: c.execute('INSERT INTO restaurant_order_items(order_id,menu_id,product_name,quantity,unit_price,line_total,ingredient_cost) VALUES(?,?,?,?,?,?,?)',(oid,*x))
        c.commit(); c.close(); return jsonify({'success':True,'order_number':order_no,'order_id':oid,'total':total,'status':'PENDING_PAYMENT'})
    except Exception as e: c.close(); return jsonify({'success':False,'message':str(e)}),400

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
