from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app import db
from sqlalchemy import text, func
from datetime import datetime, date
from app.models import (
    raw_material,
    client_payment_details,
    Client_Order_Details,
    client_workers,
    Worker_work_Details,
    Worker_Payment_Details
)

task_bp = Blueprint('tasks', __name__)


# ===================== 🔐 LOGIN CHECK DECORATOR =====================
def login_required(view_func):
    """Protect routes: redirect to login if not logged in"""
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash("⚠️ Please login first to continue.", "warning")
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

# =====================================================================
# =========================== DASHBOARD ===============================
# =====================================================================
@task_bp.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    total_sale = db.session.query(func.coalesce(func.sum(Client_Order_Details.total_amount), 0)).scalar()
    total_payment_recieve = db.session.query(func.coalesce(func.sum(client_payment_details.amount), 0)).scalar()
    due_amount = total_sale - total_payment_recieve

    total_worker_payment = db.session.query(func.coalesce(func.sum(Worker_Payment_Details.amount), 0)).scalar()
    total_raw_material_payment = db.session.query(func.coalesce(func.sum(raw_material.amount), 0)).scalar()
    total_expenditure = total_worker_payment + total_raw_material_payment
    total_profit = total_payment_recieve - total_expenditure

    summary = {
        "total_sale": total_sale,
        "total_profit": total_profit,
        "due_amount": due_amount,
        "total_expenditure": total_expenditure
    }

    # ------------------- Recent Clients -------------------
    recent_clients = db.session.execute(
        text("""
            SELECT 
            cw.client_name,
            COALESCE(o.total_orders,0) - COALESCE(p.total_payments,0) AS due_amount
            FROM client_workers cw
            LEFT JOIN (
            SELECT cw_id, SUM(total_amount) AS total_orders
            FROM client__order__details
            GROUP BY cw_id
            ) o ON cw.cw_id = o.cw_id
            LEFT JOIN (
            SELECT cw_id, SUM(amount) AS total_payments
            FROM client_payment_details
            GROUP BY cw_id
            ) p ON cw.cw_id = p.cw_id
            WHERE cw.status='Client'
            ORDER BY due_amount DESC
            LIMIT 2
        """)
    ).mappings().all()

    clients_list = [
        {"name": c["client_name"], "due_amount": c["due_amount"]}
        for c in recent_clients
    ]

    # ------------------- Recent Workers -------------------
    recent_workers = db.session.execute(
        text("""
            SELECT 
            cw.client_name,
            COALESCE(o.total_orders,0) - COALESCE(p.total_payments,0) AS remaining_amount
            FROM client_workers cw
            LEFT JOIN (
            SELECT cw_id, SUM(total_amount) AS total_orders
            FROM worker_work__details
            GROUP BY cw_id
            ) o ON cw.cw_id = o.cw_id
            LEFT JOIN (
            SELECT cw_id, SUM(amount) AS total_payments
            FROM worker__payment__details
            GROUP BY cw_id
            ) p ON cw.cw_id = p.cw_id
            WHERE cw.status='Worker'
            ORDER BY remaining_amount DESC
            LIMIT 2
        """)
    ).mappings().all()

    worker_list = [
        {"name": c["client_name"], "due_amount": c["remaining_amount"]}
        for c in recent_workers
    ]

    # ------------------- Recent Materials -------------------
    recent_materials = db.session.execute(
        text("""
            SELECT item, date, quantity, price, quantity * price AS amount 
            FROM raw_material 
            ORDER BY date DESC 
            LIMIT 3
        """)
    ).mappings().all()

    material_list = [
        {
            "name": m["item"],
            # "date": datetime.strptime(m["date"], "%Y-%m-%d") if m["date"] else None,
            "date": m["date"] if m["date"] else None,
            "quantity": m["quantity"],
            "price": m["price"],
            "amount": m["amount"],
        }
        for m in recent_materials
    ]

    clients = db.session.execute(text("SELECT client_name FROM client_workers WHERE status='Client'")).mappings().all()
    workers = db.session.execute(text("SELECT client_name FROM client_workers WHERE status='Worker'")).mappings().all()
    today = date.today().strftime("%Y-%m-%d")

    return render_template(
        "index.html",
        summary=summary,
        recent_clients=clients_list,
        recent_workers=worker_list,
        recent_materials=material_list,
        clients=clients,
        workers=workers,
        today=today
    )

# =====================================================================
# =========================== OTHER ROUTES ============================
# =====================================================================


# ---------- Raw Materials ----------
@task_bp.route("/raw_materials")
@login_required
def raw_materials():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")

    query = raw_material.query
    if search:
        query = query.filter(raw_material.item.ilike(f"%{search}%"))
    materials_pagination = query.order_by(raw_material.date.desc()).paginate(page=page, per_page=10)
    materials = materials_pagination.items

    total_inventory_value = db.session.query(db.func.sum(raw_material.amount)).scalar() or 0
    now = datetime.now()
    monthly_purchase = db.session.query(db.func.sum(raw_material.amount)).filter(
        db.extract("year", raw_material.date) == now.year,
        db.extract("month", raw_material.date) == now.month
    ).scalar() or 0

    today = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "raw_materials.html",
        materials=materials,
        materials_pagination=materials_pagination,
        total_inventory_value=total_inventory_value,
        monthly_purchase=monthly_purchase,
        search=search,
        today=today
    )


@task_bp.route("/clear_filters")
@login_required
def clear_filters():
    return redirect(url_for("tasks.raw_materials"))


# ---------------- ADD FORMS ----------------
@task_bp.route('/add_raw_material', methods=['POST'])
@login_required
def add_raw_material():
    name = request.form.get('name')
    date_str = request.form.get('date')
    quantity = request.form.get('quantity', type=int)
    price = request.form.get('price', type=float)

    if not name or not date_str or quantity is None or price is None:
        flash("Please fill all required fields", "danger")
        return redirect(url_for('tasks.raw_materials'))

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        new_material = raw_material(item=name, date=date_obj, quantity=quantity, price=price)
        db.session.add(new_material)
        db.session.commit()
        flash(f"Raw Material '{name}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('tasks.raw_materials'))


# ---------------- SHOW CLIENT ----------------
@task_bp.route("/client/<name>")
@login_required
def show_client(name):
    from datetime import datetime
    client_row = db.session.execute(
        text("SELECT cw_id, client_name FROM client_workers WHERE client_name = :name"),
        {"name": name}
    ).mappings().first()

    if not client_row:
        return "Client not found", 404

    orders = db.session.execute(
        text("""
            SELECT co_id, item, date, description, quantity, price, total_amount
            FROM client__order__details
            WHERE cw_id = :cid order by date DESC
        """),
        {"cid": client_row["cw_id"]}
    ).mappings().all()

    payments = db.session.execute(
        text("""
            SELECT cp_id, date, mode, description, amount
            FROM client_payment_details
            WHERE cw_id = :cid order by date DESC
        """),
        {"cid": client_row["cw_id"]}
    ).mappings().all()

    orders = [dict(o) for o in orders]
    payments = [dict(p) for p in payments]

    for o in orders:
        if o["date"]:
            o["date"] = datetime.strptime(str(o["date"]), "%Y-%m-%d").strftime("%d/%m/%Y")
    for p in payments:
        if p["date"]:
            p["date"] = datetime.strptime(str(p["date"]), "%Y-%m-%d").strftime("%d/%m/%Y")

    total_amount = sum(o["total_amount"] for o in orders)
    paid_amount = sum(p["amount"] for p in payments)
    due_amount = total_amount - paid_amount

    client_data = {"id": client_row["cw_id"], "name": client_row["client_name"], "items": orders, "payments": payments}

    return render_template("clients_info.html", client=client_data, total_amount=total_amount, due_amount=due_amount)


# ---------------- SHOW WORKER ----------------
@task_bp.route("/worker/<name>")
@login_required
def show_worker(name):
    from datetime import datetime
    worker_row = db.session.execute(
        text("SELECT cw_id, client_name FROM client_workers WHERE client_name = :name"),
        {"name": name}
    ).mappings().first()

    if not worker_row:
        return "Worker not found", 404

    works = db.session.execute(
        text("""
            SELECT ww_id, item, date, description, quantity, price, total_amount
            FROM worker_work__details
            WHERE cw_id = :cid order by date DESC
        """),
        {"cid": worker_row["cw_id"]}
    ).mappings().all()

    payments = db.session.execute(
        text("""
            SELECT wp_id, date, mode, description, amount
            FROM worker__payment__details
            WHERE cw_id = :cid order by date DESC
        """),
        {"cid": worker_row["cw_id"]}
    ).mappings().all()

    works = [dict(o) for o in works]
    payments = [dict(p) for p in payments]

    for o in works:
        if o["date"]:
            o["date"] = datetime.strptime(str(o["date"]), "%Y-%m-%d").strftime("%d/%m/%Y")
    for p in payments:
        if p["date"]:
            p["date"] = datetime.strptime(str(p["date"]), "%Y-%m-%d").strftime("%d/%m/%Y")

    total_amount = sum(o["total_amount"] for o in works)
    paid_amount = sum(p["amount"] for p in payments)
    remaining_amount = total_amount - paid_amount

    worker_data = {"id": worker_row["cw_id"], "name": worker_row["client_name"], "items": works, "payments": payments}

    return render_template("workers_info.html", worker=worker_data, total_amount=total_amount, remaining_amount=remaining_amount)


# ---------------- ADD CLIENT ORDER ----------------
@task_bp.route("/add_client_order", methods=["POST"])
@login_required
def add_client_order():
    client_name = request.form.get("client_name")
    item_name = request.form.get("item_name")
    description = request.form.get("description")
    order_date = request.form.get("date")
    quantity = float(request.form.get("quantity"))
    price = float(request.form.get("price"))

    cw = db.session.execute(
        text("SELECT cw_id FROM client_workers WHERE client_name = :name"), {"name": client_name}
    ).mappings().first()

    if not cw:
        flash("❌ Selected client not found!", "danger")
        return redirect(url_for("tasks.dashboard"))

    cw_id = cw["cw_id"]

    new_order = Client_Order_Details(
        item=item_name,
        date=datetime.strptime(order_date, "%Y-%m-%d"),
        description=description,
        quantity=quantity,
        price=price,
        cw_id=cw_id
    )

    db.session.add(new_order)
    db.session.commit()
    flash("✅ Client order added successfully!", "success")
    return redirect(url_for("tasks.dashboard"))


# ---------------- ADD WORKER WORK ----------------
@task_bp.route("/add_worker_work", methods=["POST"])
@login_required
def add_worker_work():
    worker_name = request.form.get("worker_name_1")
    item = request.form.get("item_name_1")
    description = request.form.get("description_1")
    work_date = request.form.get("date_1")
    quantity = float(request.form.get("quantity_1"))
    price = float(request.form.get("price_1"))

    cw = db.session.execute(
        text("SELECT cw_id FROM client_workers WHERE client_name = :name AND status='Worker'"),
        {"name": worker_name}
    ).mappings().first()

    if not cw:
        flash("❌ Selected worker not found!", "danger")
        return redirect(url_for("tasks.dashboard"))

    cw_id = cw["cw_id"]

    new_work = Worker_work_Details(
        cw_id=cw_id,
        item=item,
        description=description,
        date=datetime.strptime(work_date, "%Y-%m-%d"),
        quantity=quantity,
        price=price
    )

    db.session.add(new_work)
    db.session.commit()

    flash("✅ Worker work added successfully!", "success")
    return redirect(url_for("tasks.dashboard"))


# ---------------- ADD CLIENT PAYMENT ----------------
@task_bp.route("/add_client_payment", methods=["POST"])
@login_required
def add_client_payment():
    try:
        client_name = request.form.get("client_name_0")
        payment_date = request.form.get("date_0")
        payment_mode = request.form.get("mode_0")
        description = request.form.get("description_0")
        amount = request.form.get("amount_0")

        if not client_name or not payment_date or not payment_mode or not amount:
            flash("⚠️ Please fill all required fields!", "warning")
            return redirect(url_for("tasks.dashboard"))

        amount = int(amount)
        cw = client_workers.query.filter_by(client_name=client_name, status="Client").first()

        if not cw:
            flash("❌ Selected client not found!", "danger")
            return redirect(url_for("tasks.dashboard"))

        new_payment = client_payment_details(
            cw_id=cw.cw_id,
            date=datetime.strptime(payment_date, "%Y-%m-%d"),
            mode=payment_mode,
            description=description,
            amount=amount
        )

        db.session.add(new_payment)
        db.session.commit()

        flash("✅ Client payment added successfully!", "success")
        return redirect(url_for("tasks.dashboard"))

    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error adding payment: {e}", "danger")
        return redirect(url_for("tasks.dashboard"))


# ---------------- ADD WORKER PAYMENT ----------------
@task_bp.route("/add_worker_payment", methods=["POST"])
@login_required
def add_worker_payment():
    worker_name = request.form.get("worker_name_2")
    payment_date = request.form.get("date_2")
    mode = request.form.get("mode_2")
    description = request.form.get("description_2")
    amount = float(request.form.get("amount_2"))

    cw = db.session.execute(
        text("SELECT cw_id FROM client_workers WHERE client_name = :name AND status='Worker'"),
        {"name": worker_name}
    ).mappings().first()

    if not cw:
        flash("❌ Selected worker not found!", "danger")
        return redirect(url_for("tasks.dashboard"))

    cw_id = cw["cw_id"]

    new_payment = Worker_Payment_Details(
        cw_id=cw_id,
        date=datetime.strptime(payment_date, "%Y-%m-%d"),
        mode=mode,
        description=description,
        amount=amount
    )

    db.session.add(new_payment)
    db.session.commit()

    flash("✅ Worker payment added successfully!", "success")
    return redirect(url_for("tasks.dashboard"))



# ---------------- ALL CLIENTS PAGE ----------------
@task_bp.route("/all_clients")
@login_required
def all_clients():

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()

    query = client_workers.query.filter_by(status="Client")
    if search:
        query = query.filter(client_workers.client_name.ilike(f"%{search}%"))
    
    recent_clients = db.session.execute(
        text("""
            SELECT 
            cw.client_name,
            COALESCE(o.total_orders,0) - COALESCE(p.total_payments,0) AS due_amount
            FROM client_workers cw
            LEFT JOIN (
            SELECT cw_id, SUM(total_amount) AS total_orders
            FROM client__order__details
            GROUP BY cw_id
            ) o ON cw.cw_id = o.cw_id
            LEFT JOIN (
            SELECT cw_id, SUM(amount) AS total_payments
            FROM client_payment_details
            GROUP BY cw_id
            ) p ON cw.cw_id = p.cw_id
            WHERE cw.status='Client'
            
        """)
    ).mappings().all()

    # Pagination
    clients_pagination = query.order_by(client_workers.client_name.asc()).paginate(page=page, per_page=8)
    clients_list = [{"name": c.client_name, "due_amount": c.due_amount} for c in recent_clients]  # placeholder due

    total_clients = query.count()
    

    return render_template(
        "all_client_details.html",
        clients=clients_list,
        clients_pagination=clients_pagination,
        total_clients=total_clients,
        search=search
    )


# ---------------- ADD NEW CLIENT ----------------
@task_bp.route("/add_client", methods=["POST"])
@login_required
def add_client():
    name = request.form.get("name")
    contact = request.form.get("contact")  # optional

    if not name:
        flash("Client name is required!", "danger")
        return redirect(url_for("tasks.all_clients"))

    try:
        new_client = client_workers(client_name=name, status="Client")
        db.session.add(new_client)
        db.session.commit()
        flash(f"Client '{name}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error adding client: {e}", "danger")

    return redirect(url_for("tasks.all_clients"))



# ---------------- ALL WORKERS PAGE ----------------
@task_bp.route("/all_workers")
@login_required
def all_workers():

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()

    query = client_workers.query.filter_by(status="Worker")
    if search:
        query = query.filter(client_workers.client_name.ilike(f"%{search}%"))
    
    recent_workers = db.session.execute(
        text("""
            SELECT 
            cw.client_name,
            COALESCE(o.total_orders,0) - COALESCE(p.total_payments,0) AS remaining_amount
            FROM client_workers cw
            LEFT JOIN (
            SELECT cw_id, SUM(total_amount) AS total_orders
            FROM worker_work__details
            GROUP BY cw_id
            ) o ON cw.cw_id = o.cw_id
            LEFT JOIN (
            SELECT cw_id, SUM(amount) AS total_payments
            FROM worker__payment__details
            GROUP BY cw_id
            ) p ON cw.cw_id = p.cw_id
            WHERE cw.status='Worker'
        """)
    ).mappings().all()

    # Pagination
    workers_pagination = query.order_by(client_workers.client_name.asc()).paginate(page=page, per_page=8)
    workers_list = [{"name": w.client_name, "due_amount": w.remaining_amount} for w in recent_workers]  # placeholder due

    total_workers = query.count()
    

    return render_template(
        "all_worker_details.html",
        workers=workers_list,
        workers_pagination=workers_pagination,
        total_workers=total_workers,
        search=search
    )


# ---------------- ADD NEW CLIENT ----------------
@task_bp.route("/add_worker", methods=["POST"])
@login_required
def add_worker():
    name = request.form.get("name")
    contact = request.form.get("contact")  # optional

    if not name:
        flash("Client name is required!", "danger")
        return redirect(url_for("tasks.all_workers"))

    try:
        new_worker = client_workers(client_name=name, status="Worker")
        db.session.add(new_worker)
        db.session.commit()
        flash(f"Worker '{name}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error adding Worker: {e}", "danger")

    return redirect(url_for("tasks.all_workers"))