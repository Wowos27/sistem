from . import app, db, bcrypt, jwt, User, Role
from flask import request, render_template, redirect, url_for, jsonify, session, flash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies

@app.route('/masuk')
def masuk():
    return render_template('admin/admin.html')

# Endpoint untuk membuat token
@app.route('/proses_masuk', methods=['POST'])
def proses_masuk():
    username = request.json['username']
    password = request.json['password']

    # Mencari pengguna berdasarkan username
    user = User.query.filter_by(username=username).first()

    if not user:
        return "Username salah", 400

    # Memverifikasi password
    if bcrypt.check_password_hash(user.password, password):
        access_token = create_access_token(identity=username)
        session['jwt_token'] = access_token
        session['username'] = username
        return access_token
    else:
        return "Password salah", 400

# Endpoint yang memerlukan autentikasi
@app.route('/keluar')
def keluar():
    # Hapus token dari cookie (anda bisa menghapus token dari header juga jika tidak menggunakan cookie)
    response = jsonify({'message': 'Logout berhasil'})
    unset_jwt_cookies(response)
    session.pop('jwt_token', None)
    session.pop('username', None)
    flash('Sukses Logout')
    return redirect(url_for('masuk'))

@jwt.expired_token_loader
def expired_token_callback():
    return redirect(url_for('masuk'))

@app.route('/bikin_akun', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # jwt_required()
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"msg": "Username and password are required"}), 400

        # Cek apakah username sudah ada
        if User.query.filter_by(username=username).first():
            return jsonify({"msg": "Username already exists"}), 400

        # Hash password sebelum disimpan
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Membuat pengguna baru
        user = User(username=username, password=hashed_password, active=True)
        db.session.add(user)
        db.session.commit()

        # Logout setelah registrasi berhasil
        response = jsonify({'message': 'Logout berhasil'})
        unset_jwt_cookies(response)
        session.pop('jwt_token', None)
        session.pop('username', None)
        flash('Sukses Logout')
        return redirect(url_for('masuk', msg='Registration Successful'))

    return render_template('admin/register.html')

