from app import app,db
#ssl_context='adhoc'
from flask import request, jsonify
import datetime
#ssl_context='adhoc'
@app.route('/chatbot/get')
def chatbot():
  userText = request.args.get('msg')
  tanggal = datetime.datetime.now()
  tanggal_baru = tanggal.strftime('%Y-%m-%d %H:%M:%S')
  import chatbot
  respon = chatbot.generate_response(userText)
  print(respon)
  return respon
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", debug=True, port=4040)