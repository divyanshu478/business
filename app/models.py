from app import db

class client_workers(db.Model) :
    cw_id = db.Column(db.Integer, primary_key = True)
    client_name = db.Column(db.String(100), nullable = False)
    status = db.Column(db.String(100), nullable = False)


    client_order = db.relationship('Client_Order_Details', backref='student', lazy=True)
    client_payment = db.relationship('client_payment_details', backref='student', lazy=True)


class Client_Order_Details(db.Model) :
    co_id = db.Column(db.Integer, primary_key = True)
    item = db.Column(db.String(100), nullable = False)
    date = db.Column(db.Date, nullable = False)
    description = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable = False)
    price = db.Column(db.Integer, nullable = False)
    total_amount = db.Column(db.Integer, db.Computed('quantity * price'))    

    cw_id = db.Column(db.Integer, db.ForeignKey('client_workers.cw_id'), nullable=False)



class client_payment_details(db.Model):
    cp_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable = False)
    mode = db.Column(db.String(100))
    description = db.Column(db.String(100))
    amount = db.Column(db.Integer, nullable = False) 

    cw_id = db.Column(db.Integer, db.ForeignKey('client_workers.cw_id'), nullable=False)
   

class raw_material(db.Model):
    raw_id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100), nullable = False)
    date = db.Column(db.Date, nullable = False)
    quantity = db.Column(db.Integer, nullable = False)
    price = db.Column(db.Float, nullable = False)
    amount = db.Column(db.Integer, db.Computed('quantity * price'))




class Worker_work_Details(db.Model) :
    ww_id = db.Column(db.Integer, primary_key = True)
    item = db.Column(db.String(100), nullable = False)
    date = db.Column(db.Date, nullable = False)
    description = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable = False)
    price = db.Column(db.Integer, nullable = False)
    total_amount = db.Column(db.Integer, db.Computed('quantity * price'))   

    cw_id = db.Column(db.Integer, db.ForeignKey('client_workers.cw_id'), nullable=False)



class Worker_Payment_Details(db.Model):
    wp_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable = False)
    mode = db.Column(db.String(100))
    description = db.Column(db.String(100))
    amount = db.Column(db.Integer, nullable = False) 

    cw_id = db.Column(db.Integer, db.ForeignKey('client_workers.cw_id'), nullable=False)



