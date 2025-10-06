from app import create_app, db
from app.models import client_workers, Client_Order_Details, client_payment_details, raw_material




app = create_app()

with app.app_context() :
    db.create_all()



if __name__ == "__main__" :
    app.run(debug=True)