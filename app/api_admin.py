from . import app,mysql,db,allowed_file
from flask import render_template, request, jsonify, redirect, url_for,session,g
import os,textwrap, locale, json, uuid, time
import pandas as pd
from PIL import Image
from io import BytesIO
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.before_request
def before_request():
    g.con = mysql.connection.cursor()
@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'con'):
        g.con.close()
        
def do_image(do, table, id):
    try:
        if do == "delete":
            filename = get_image_filename(table, id)
            delete_image(filename)
            return True
        file = request.files['gambar']
        if file is None or file.filename == '':
            return "default.jpg"
        else:
            filename = get_image_filename(table, id)
            delete_image(filename)
            return resize_and_save_image(file, table, id)
    except KeyError:
        if do == "edit":
            if table =="galeri":
                return True
            reset = request.form['reset']
            print(reset)
            if reset=="true":
                g.con.execute(f"UPDATE {table} SET gambar = %s WHERE id = %s", ("default.jpg", id))
                mysql.connection.commit()
        return "default.jpg"# Tangkap kesalahan jika kunci 'gambar' tidak ada dalam request.files
    except FileNotFoundError:
        pass  # atau return "File tidak ditemukan."
    except Exception as e:
        print(str(e))
        return str(e)

def resize_and_save_image(file, table=None, id=None):
    img = Image.open(file).convert('RGB').resize((600, 300))
    img_io = BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    random_name = uuid.uuid4().hex + ".jpg"
    destination = os.path.join(app.config['UPLOAD_FOLDER'], random_name)
    img.save(destination)
    if table and id:
        g.con.execute(f"UPDATE {table} SET gambar = %s WHERE id = %s", (random_name, id))
        mysql.connection.commit()
        return True
    else:
        return random_name
def get_image_filename(table, id):
    g.con.execute(f"SELECT gambar FROM {table} WHERE id = %s", (id,))
    result = g.con.fetchone()
    if result == "default.jpg":
        return None
    return result[0] if result else None

def delete_image(filename):
    if filename == "default.jpg":
        return True
    if filename:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(image_path):
            os.remove(image_path)

def fetch_data_and_format(query):
    g.con.execute(query)
    data = g.con.fetchall()
    column_names = [desc[0] for desc in g.con.description]
    info_list = [dict(zip(column_names, row)) for row in data]
    return info_list

def fetch_data_and_format1(query):
    # Eksekusi query dan ambil hasil
    g.con.execute(query)
    data = g.con.fetchall()

    # Menampilkan hasil untuk debug
    print(data)

    # Asumsikan data adalah list dengan satu elemen yang merupakan string JSON
    if data:
        json_string = data[0][0]  # Ambil string JSON dari tuple
        
        # Ganti single quotes dengan double quotes
        json_string = json_string.replace("'", '"').strip()
        try:
            # Menggunakan JSON parsing untuk memvalidasi dan memperbaiki format JSON
            json_data = json.loads(json_string)
            # Mengembalikan data yang sudah diparse
            return json_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    return None

def fetch_years(query):
    g.con.execute(query)
    data_thn = g.con.fetchall()
    thn = [{'tahun': str(sistem[0])} for sistem in data_thn]
    return thn

def insert_data_from_dataframe(df, table):
    for index, row in df.iterrows():
        sql = f"INSERT INTO {table} (no, uraian, anggaran, realisasi, `lebih/(kurang)`, tahun) VALUES (%s, %s, %s, %s, %s, %s)"
        print(row['lebih/(kurang)'])
        if row['no'] == 'Z' or row['no'] == 'Y':
            row['no'] = ""
        g.con.execute(sql, (row['no'], row['uraian'], str(format_currency(row['anggaran'])), str(format_currency(row['realisasi'])), str(format_currency(row['lebih/(kurang)'])), row['thn']))
    mysql.connection.commit()
fields_mono = [
    {"name": "Jumlah Penduduk", "value": "jpenduduk"},
    {"name": "Jumlah KK", "value": "jkk"},
    {"name": "Laki-Laki", "value": "laki"},
    {"name": "Perempuan", "value": "perempuan"},
    {"name": "Jumlah KK Prasejahtera", "value": "jkkprese"},
    {"name": "Jumlah KK Sejahtera", "value": "jkkseja"},
    {"name": "Jumlah KK Kaya", "value": "jkkkaya"},
    {"name": "Jumlah KK Sedang", "value": "jkksedang"},
    {"name": "Jumlah KK Miskin", "value": "jkkmiskin"},
    {"name": "Buruh", "value": "buruh"},
    {"name": "Petani", "value": "petani"},
    {"name": "Peternak", "value": "peternak"},
    {"name": "Pedagang", "value": "pedagang"},
    {"name": "Tukang Kayu", "value": "tukangkayu"},
    {"name": "Tukang Batu", "value": "tukangbatu"},
    {"name": "Penjahit", "value": "penjahit"},
    {"name": "Pegawai Sipil/Polisi/Tentara", "value": "asn"},
    {"name": "Pensiunan", "value": "pensiunan"},
    {"name": "Perangkat desa", "value": "perangkatdesa"},
    {"name": "Jasa / Wiraswasta", "value": "jasa_wiraswasta"},
    {"name": "Pengrajin Batik", "value": "pengrajinbatik"},
    {"name": "Dll", "value": "dll"}
]
#halaman admin
@app.route('/admin/dashboard')
def dashboard():
    info_mono=fetch_data_and_format("SELECT * FROM monografi")
    info_geo=fetch_data_and_format("SELECT * FROM wilayah")
    fields_geo=[{"name":"Sawah Teri","value":"sawahteri"},{"name":"Luas Wilayah","value":"luas"},{"name":"Sawah Hutan","value":"sawahhu"},{"name":"Pemukiman","value":"pemukiman"}]	
    return render_template('admin/dashboard.html',info_mono=info_mono,info_geo=info_geo, fields_mono=fields_mono,fields_geo=fields_geo)

#sejarah
@app.route('/admin/infodesa')
def admininfodesa():
    info_list = fetch_data_and_format("SELECT * FROM sejarah_desa")
    return render_template("admin/infodesa.html", info_list = info_list)

#tambah info
@app.route('/tambah_info', methods=['POST'])
@jwt_required()
def tambah_info():
    sejarah = request.form['sejarah']
    visi = request.form['visi']
    misi = request.form['misi']
    try:
        g.con.execute("INSERT INTO sejarah (sejarah , visi, misi) VALUES (%s,%s,%s)",(sejarah , visi, misi))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

#edit info data
@app.route('/edit_info', methods=['PUT'])
@jwt_required()
def infoedit():
    id = request.form['id']
    sejarah = request.form['sejarah']
    visi = request.form['visi']
    misi = request.form['misi']
    try:
        g.con.execute("UPDATE sejarah_desa SET sejarah = %s, visi = %s, misi = %s WHERE id = %s",(sejarah,visi,misi,id))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/edit_sejarah', methods=['GET','PUT'])
def sejarahedit():
    if request.method == 'PUT':
        jwt_required()
        sejarah = request.form['sejarah']
        try:
            g.con.execute("UPDATE sejarah_desa SET sejarah = %s WHERE id = 1",(str(sejarah),))
            mysql.connection.commit()
            return jsonify({"msg":"SUKSES"})
        except Exception as e:
            print(str(e))
            return jsonify({"error": str(e)})
    else:
        info=fetch_data_and_format("SELECT * FROM sejarah_desa WHERE id = 1")
        return render_template("admin/editsejarah.html",info=info)
    
#visimisi
@app.route('/admin/visimisi')
def adminvisimisi():
    info_list = fetch_data_and_format("SELECT * FROM sejarah_desa")
    return render_template("admin/visimisi.html", info_list = info_list)

@app.route('/admin/visiedit', methods=['PUT'])
@jwt_required()
def adminvisiedit():
    visi = request.form['visi']
    visi = str(visi)
    try:
        g.con.execute("UPDATE sejarah_desa SET visi= %s WHERE id = 1",(visi,))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/admin/misiedit', methods=['PUT'])
@jwt_required()
def adminmisiedit():
    misi = request.form['misi']
    misi = str(misi)
    try:
        g.con.execute("UPDATE sejarah_desa SET misi= %s WHERE id = 1",(misi,))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
    
#berita
@app.route('/admin/berita')
def admindberita():
    info_list=fetch_data_and_format("SELECT * FROM berita order by id DESC")
    return render_template("admin/berita.html", info_list = info_list)

@app.route('/admin/tambah_berita', methods=['POST'])
@jwt_required()
def tambah_berita():
    judul = request.form['judul']
    link = '_'.join(filter(None, [judul.replace("#", "").replace("?", "").replace("/", "").replace(" ", "_")]))
    deskripsi = request.form['deskripsi']
    deskripsi = textwrap.shorten(deskripsi, width=75, placeholder="...")
    deskripsifull = request.form['deskripsifull']
    try: 
        random_name = do_image("tambah","berita","")
        g.con.execute("INSERT INTO berita (judul, gambar , deskripsi, deskripsifull, link ) VALUES (%s,%s,%s,%s,%s)",(judul,random_name,deskripsi,deskripsifull,link))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        str(e)
        return jsonify({"error": str(e)})
@app.route('/admin/edit_berita', methods=['PUT'])
@jwt_required()
def berita_edit():
    id = request.form['id']
    judul = request.form['judul']
    link = '_'.join(filter(None, [judul.replace("#", "").replace("?", "").replace("/", "").replace(" ", "_")]))
    deskripsi = request.form['deskripsi']
    deskripsi = textwrap.shorten(deskripsi, width=75, placeholder="...")
    deskripsifull = request.form['deskripsifull']
    try:
        status = do_image("edit","berita",id)
        g.con.execute("UPDATE berita SET judul = %s, deskripsi = %s, deskripsifull = %s, link = %s  WHERE id = %s",(judul,deskripsi,deskripsifull,link,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/hapus_berita', methods=['DELETE'])
@jwt_required()
def hapus_berita():
    id = request.form['id']
    try:
        do_image("delete","berita",id)
        g.con.execute("DELETE FROM berita WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
#function di render_template
@app.template_filter('format_currency')
def format_currency(value):
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
    return locale.currency(value, grouping=True, symbol='Rp')
@app.template_filter('clean_currency')
def clean_currency(value):
    """Remove 'Rp', dots, and spaces, then convert to float"""
    cleaned_value = value.replace('Rp', '').replace('RP', '').replace('.', '').replace(',', '.').strip()
    return float(cleaned_value)
@app.template_filter('angka_ke_huruf')
def angka_ke_huruf(n):
    if 1 <= n <= 26:
        return chr(n + 64)
    else:
        return "Angka harus antara 1 dan 26."

def set_urutan_default(info_list):
    urutan = {}
    for i in fetch_data_and_format(f"SELECT * FROM realisasi_{info_list} ORDER BY id"):
        tahun = i["tahun"]
        urutan.setdefault(tahun, []).append(
            {"id": f"{i['id']}", "children": [{"id": anak.strip("'")} for anak in i["onclick"].replace("toggleDetails(", "").replace(")", "").split(",")]} 
            if i["class"].strip() == "clickable-row" else {"id": f"{i['id']}"}
        ) if i["class"] != "hidden-row" else None
    print(urutan)
    return urutan

def set_urutan(column, years):
    urutan = {}
    for year in years:
        g.con.execute(f"SELECT {column} FROM urutan WHERE tahun = %s", (year["tahun"],))
        result= g.con.fetchone()
        if result:
            try:
                urutan.update(json.loads(str(result[0]).replace("'", '"')))
            except json.JSONDecodeError:
                print("Error: Hasil bukan JSON yang valid:", result)
    return urutan if urutan else set_urutan_default(column)
@app.route('/admin/dana')
def admindana():
    info_list = fetch_data_and_format("SELECT * FROM tabel_anggaran ORDER BY no")
    info_list2 = fetch_data_and_format("SELECT * FROM tabel_transaksi ORDER BY no")
    gabung = fetch_data_and_format("SELECT * FROM gabung_anggaran_transaksi")
    info_list3 = [{**j, 
                    'realisasi': (realisasi := sum( int(k['nominal']) for i in gabung if i['id_tabel_anggaran'] == j['id'] for k in info_list2 if i['id_transaksi'] == k['id'] )),
                    'lebih_kurang': int(j['anggaran']) - realisasi} for j in info_list ]
    gabung_nota = fetch_data_and_format("SELECT * FROM gabung_tabel_transaksi_nota")
    thn = fetch_years("SELECT tahun FROM tabel_anggaran GROUP BY tahun")
    summary = []
    for h in thn:
        pendapatan = [k for k in info_list3 if k['tahun'] == h['tahun'] and k['type'] == "pendapatan"]
        pengeluaran = [k for k in info_list3 if k['tahun'] == h['tahun'] and k['type'] == "pengeluaran"]
        item = {
            'tahun': h['tahun'],
            'jml_anggaran_pendapatan': (jml_anggaran_pendapatan := sum(int(k['anggaran']) for k in pendapatan)),
            'jml_realisasi_pendapatan':  (jml_realisasi_pendapatan  := sum(int(k['realisasi']) for k in pendapatan)),
            'jml_anggaran_pengeluaran':  (jml_anggaran_pengeluaran  := sum(int(k['anggaran']) for k in pengeluaran)),
            'jml_realisasi_pengeluaran': (jml_realisasi_pengeluaran := sum(int(k['realisasi']) for k in pengeluaran)),
        }
        item.update({
            'jml_lebih_kurang_pendapatan': (jml_lebih_kurang_pendapatan := format_currency(item['jml_anggaran_pendapatan'] - item['jml_realisasi_pendapatan'])),
            'jml_lebih_kurang_pengeluaran': (jml_lebih_kurang_pengeluaran := format_currency(item['jml_anggaran_pengeluaran'] - item['jml_realisasi_pengeluaran'])),
            'summary_pendapatan': (
                f"Realisasi Pendapatan melebihi Estimasi yang diprediksi. Dari total anggaran sebesar {format_currency(int(jml_anggaran_pendapatan))}, realisasi pendapatan mecapai {format_currency(int(jml_realisasi_pendapatan))}, dengan selisih lebih besar {(jml_lebih_kurang_pendapatan)}" if item['jml_anggaran_pendapatan'] < item['jml_realisasi_pendapatan'] else
                f"Realisasi Pendapatan kurang dari Estimasi yang diprediksi. Dari total anggaran sebesar {format_currency(int(jml_anggaran_pendapatan))}, realisasi pendapatan mecapai {format_currency(int(jml_realisasi_pendapatan))}, dengan selisih lebih besar {(jml_lebih_kurang_pendapatan)}" if item['jml_anggaran_pendapatan'] > item['jml_realisasi_pendapatan'] else
                f"Realisasi Pendapatan sesuai Estimasi yang diprediksi. Dari total anggaran sebesar {format_currency(int(jml_anggaran_pendapatan))}, realisasi pendapatan mecapai {format_currency(int(jml_realisasi_pendapatan))}, dengan selisih lebih besar {(jml_lebih_kurang_pendapatan)}"
            ),
            'summary_pengeluaran': (
                f"Realisasi Pengeluaran untuk seluruh bidang kegiatan desa lebih tinggi dibandingkan dengan anggaran yang telah diterapkan. Dari total anggaran sebesar {format_currency(int(jml_anggaran_pengeluaran))}, realisasi pengeluaran mencapai {format_currency(int(jml_realisasi_pengeluaran))}. Terdapat selisih kurang sebesar {(jml_lebih_kurang_pengeluaran)}, yang menunjukan adanya pengeluaran yang melebihi anggaran di beberapa bidang" if item['jml_anggaran_pengeluaran'] < item['jml_realisasi_pengeluaran'] else
                f"Realisasi Pengeluaran untuk seluruh bidang kegiatan desa lebih rendah dibandingkan dengan anggaran yang telah diterapkan. Dari total anggaran sebesar {format_currency(int(jml_anggaran_pengeluaran))}, realisasi pengeluaran mencapai {format_currency(int(jml_realisasi_pengeluaran))}. Terdapat selisih lebih besar {(jml_lebih_kurang_pengeluaran)}, yang menunjukan efisiensi dalam penggunaan dana di beberapa bidang" if item['jml_anggaran_pengeluaran'] > item['jml_realisasi_pengeluaran'] else
                f"Realisasi Pengeluaran untuk seluruh bidang kegiatan desa sama dengan dibandingkan dengan anggaran yang telah diterapkan. Dari total anggaran sebesar {format_currency(int(jml_anggaran_pengeluaran))}, realisasi pengeluaran mencapai {format_currency(int(jml_realisasi_pengeluaran))}. Tidak Terdapat selisih yang menunujukan efisiensi dalam penggunaan dana di seluruh bidang"
            ),
        })
        summary.append(item)
        
    list_nota=fetch_data_and_format("SELECT * FROM nota order by id DESC")
    return render_template("admin/dana_transaksi.html", info_list=info_list, info_list2=info_list2, info_list3=info_list3, tahun=thn, summary=summary, list_nota = list_nota)

@app.route('/admin/dana/ubah_urutan', methods=['PUT'])
@jwt_required()
def ubah_urutan_dana():
    data = request.json.get('nestable', [])
    data_json = json.loads(data)
    print(data_json)

    def update_children(data):
        children_list = []
        rab_list = []  # Variabel untuk menyimpan rab

        for i in data:
            year, tabel, child_id, rab = str(i['id']).split('-')
            g.con.execute(f"UPDATE realisasi_{tabel} SET class = 'hidden-row', detail = %s, onclick = '' WHERE id = %s AND tahun = %s",
                        (f"{year}-{tabel}-{child_id}", child_id, year))
            
            children_list.append({"id": child_id})
            rab_list.append(rab)  # Tambahkan rab ke rab_list

        # Kembalikan kedua data secara terpisah
        return {"children": children_list, "rab": rab_list}

    def update_urutan(data):
        urutan_baru = {}

        for i in data:
            tahun, tabel, id_, rab = str(i['id']).split('-')
            entry = {"id": id_}
            
            # SELECT class terlebih dahulu
            g.con.execute(f"SELECT class, detail, onclick FROM realisasi_{tabel} WHERE id = %s AND tahun = %s", (id_, tahun))
            result = g.con.fetchone()

            if result:
                class_value, detail_value, onclick_value = result

                # Jika class 'hidden-row', update menjadi 'hidden-row, clickable-row'
                if class_value == 'hidden-row':
                    new_class = 'hidden-row, clickable-row'
                else:
                    new_class = 'clickable-row'

                # Lakukan UPDATE sesuai kondisi
                g.con.execute(f"UPDATE realisasi_{tabel} SET class = %s, detail = %s, onclick = %s WHERE id = %s AND tahun = %s", 
                            (new_class, detail_value, onclick_value, id_, tahun))

            # Tambahkan entry parent ke dalam urutan_baru
            urutan_baru.setdefault(tahun, []).append(entry)

            # Tambahkan children jika ada
            if 'children' in i:
                # Dapatkan daftar children dan tambahkan mereka ke dalam urutan_baru setelah parent
                children_data = update_children(i['children'])
                rab_children = children_data['rab']  # Ambil data rab
                children = children_data['children']  # Ambil data children

                if '1' in rab_children:
                    onclick_value = f"toggleDetails('{','.join([str(j['id']) for j in i['children']][:-1])}')"
                    g.con.execute(f"UPDATE realisasi_{tabel} SET class = 'clickable-row', detail = '', onclick = %s, punya_rab = %s WHERE id = %s AND tahun = %s",
                                (onclick_value, 1, id_, tahun))
                else:
                    onclick_value = f"toggleDetails('{','.join([str(j['id']) for j in i['children']][:-1])}')"
                    g.con.execute(f"UPDATE realisasi_{tabel} SET class = 'clickable-row', detail = '', onclick = %s WHERE id = %s AND tahun = %s",
                                (onclick_value, id_, tahun))

                urutan_baru.setdefault(tahun, []).extend(children)
        
        print(urutan_baru)
        mysql.connection.commit()
        return urutan_baru

    def get_all_years():
        g.con.execute("SELECT DISTINCT tahun FROM urutan")
        return [row[0] for row in g.con.fetchall()]

    def update_database(tabel, urutan, tahun):
        valid_tables = ["pendapatan", "belanja", "pembiayaan"]
        if tabel in valid_tables:
            g.con.execute(f"UPDATE urutan SET {tabel} = %s WHERE tahun = %s", (urutan, tahun))
            mysql.connection.commit()
        else:
            raise ValueError("Invalid table name")

    all_years = get_all_years()
    init_tahun = str(data_json[0]['id']).split('-')[0] if data_json else ""

    if init_tahun and init_tahun not in all_years:
        g.con.execute("INSERT INTO urutan (tahun) VALUES (%s)", (init_tahun,))
        mysql.connection.commit()

    for i in data_json:
        _, tabel, id_,rab = str(i['id']).split('-')
        urutan = update_urutan(data_json)
        update_database(tabel, urutan, init_tahun)

    return jsonify({"msg": "SUKSES"})

@app.route('/admin/dana/upload_file', methods=['POST'])
@jwt_required()
def upload_file_dana():
    tahun = request.form['tahun']
    kategori = request.form["kategori"]
    id = request.form["id"]
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file_upload = request.files['file']

    if file_upload.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400
    try:
        random_name = uuid.uuid4().hex + os.path.splitext(file_upload.filename)[1]
        destination = os.path.join(app.config['UPLOAD_NOTA'], random_name)
        file_upload.save(destination)
        g.con.execute(f"UPDATE realisasi_{kategori} SET nota = %s WHERE id = %s",(random_name, id))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
def hapus_urutan_lama(id, kategori, tahun_lama):
    try:
        g.con.execute(f"SELECT {kategori} FROM urutan WHERE tahun = %s", (tahun_lama,))
        result = g.con.fetchone()
        if result:
            urutan = json.loads(result[0].replace("'", '"'))
            urutan = [item for item in urutan[tahun_lama] if item.get('id') != id] if isinstance(urutan, list) else None
            if urutan is None:
                return jsonify({"error": "Unexpected JSON structure"}), 400
            g.con.execute(f"UPDATE urutan SET {kategori} = %s WHERE tahun = %s", (json.dumps(urutan), tahun_lama))
            g.con.connection.commit()
            return jsonify({"msg": "SUKSES"})
        return jsonify({"error": "Data tidak ditemukan"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def insert_or_update_urutan(new_id, kategori, tahun_baru, parent_id=None):
    try:
        print(f"Checking if tahun_baru {tahun_baru} exists in urutan")
        # Cek apakah tahun baru sudah ada
        g.con.execute("SELECT COUNT(*) FROM urutan WHERE tahun = %s", (tahun_baru,))
        tahun_exists = g.con.fetchone()[0] > 0
        print(f"Tahun exists: {tahun_exists}")

        if not tahun_exists:
            # Tahun baru, buat entri baru
            urutan = [{"id": new_id}]
            query = f"INSERT INTO urutan ({kategori}, tahun) VALUES (%s, %s)"
            print(f"Inserting new urutan with query: {query}, params: {urutan}, {tahun_baru}")
            g.con.execute(query, (json.dumps(urutan), tahun_baru))
        else:
            # Tahun sudah ada, update entri
            g.con.execute(f"SELECT {kategori} FROM urutan WHERE tahun = %s", (tahun_baru,))
            result = g.con.fetchone()

            # Debugging hasil query
            print(f"Result of urutan fetch: {result}")

            if result:
                urutan = json.loads(result[0].replace("'", '"'))  # Convert string to JSON
                print(urutan)
                # Ambil list dari tahun yang sesuai
                if tahun_baru in urutan:
                    id_list = urutan[tahun_baru]  # Ini adalah list yang berisi dict dengan 'id'
                    print(id_list)
                    if parent_id:
                        # Insert setelah parent_id jika ada
                        for idx, item in enumerate(id_list):
                            print(idx)
                            if item['id'] == parent_id:
                                id_list.insert(idx + 1, {'id': new_id})
                                break
                    else:
                        print(parent_id)
                        # Tambahkan ke list id
                        id_list.append({"id": new_id})
                    
                    # Simpan perubahan kembali ke urutan
                    urutan[tahun_baru] = id_list
                    print(urutan[tahun_baru])
                    g.con.execute(f"UPDATE urutan SET {kategori} = %s WHERE tahun = %s", (json.dumps(urutan), tahun_baru))

                else:
                    # Jika tahun belum ada, tambahkan tahun dan id baru
                    urutan[tahun_baru] = [{"id": new_id}]
                    print(urutan[tahun_baru])
                    g.con.execute(f"UPDATE urutan SET {kategori} = %s WHERE tahun = %s", (json.dumps(urutan), tahun_baru))

        g.con.connection.commit()
        print(f"Urutan table updated successfully for tahun: {tahun_baru}")
        return jsonify({"msg": "SUKSES"})

    except json.JSONDecodeError:
        print("JSON Decode Error occurred")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/admin/dana/tambah/tahun', methods=['POST'])
@jwt_required()
def tambah_tahun_dana():
    tahun = request.form['tahun']
    # Query untuk mengambil semua tahun yang ada di database
    g.con.execute("SELECT tahun FROM urutan GROUP BY tahun")
    thn = [row[0] for row in g.con.fetchall()]  # Mengambil semua tahun sebagai list
    # Jika tahun belum ada di database, tambahkan
    if tahun not in thn:
        g.con.execute("INSERT INTO urutan (tahun) VALUES (%s)", (tahun,))
        g.con.connection.commit()
        return jsonify({"msg": "SUKSES"})
    else:
        # Jika tahun sudah ada, berikan pesan error
        return jsonify({"msg": "Maaf, Tahun sudah ada"}), 500


@app.route('/admin/dana_new/tambah/id', methods=['POST'])
@jwt_required()
def tambah_id_dana_new():
    tahun_lama = request.json.get('tahun_lama')
    tahun_baru = request.json.get('tahun_baru')
    kategori = request.json.get("kategori")
    no = request.json.get('no')
    
    try:
        if kategori == 'anggaran':
            uraian   = request.json.get('uraian')  
            anggaran = request.json.get('anggaran')
            anggaran = anggaran.replace(".", "")
            type     = request.json.get('type')
            # Menyisipkan data
            g.con.execute(f"INSERT INTO tabel_anggaran (no, uraian, anggaran, type, tahun) VALUES (%s, %s, %s, %s, %s)", (no, uraian, anggaran, type, tahun_baru))
            # Commit perubahan
            g.con.connection.commit()
        else :
            tanggal = request.json.get('tanggal')
            keterangan = request.json.get('keterangan')
            nominal   = request.json.get('nominal')
            alokasi   = request.json.get('alokasi')
            id_anggaran = alokasi.split("-")[0]
            alokasi = alokasi.split("-")[1]
            g.con.execute(f"INSERT INTO tabel_transaksi (no, tanggal, keterangan, nominal, alokasi, tahun) VALUES (%s, %s, %s, %s, %s, %s)", (no, tanggal, keterangan, nominal, alokasi, tahun_baru))
            new_id = g.con.lastrowid
            g.con.execute(f"INSERT INTO gabung_anggaran_transaksi (id_tabel_anggaran, id_transaksi) VALUES (%s, %s)", (id_anggaran, new_id))
            # Commit perubahan
            g.con.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/admin/dana/tambah/id', methods=['POST'])
@jwt_required()
def tambah_id_dana():
    tahun_lama = request.json.get('tahun_lama')
    tahun_baru = request.json.get('tahun_baru')
    kategori = request.json.get("kategori")
    no = request.json.get('no')
    uraian = request.json.get('uraian')
    anggaran = request.json.get('anggaran')
    realisasi = request.json.get('realisasi')
    lebih_kurang = request.json.get('lebih_kurang')
    
    try:
        # Menyisipkan data
        g.con.execute(f"INSERT INTO realisasi_{kategori} (no, uraian, anggaran, realisasi, `lebih/(kurang)`, tahun) VALUES (%s, %s, %s, %s, %s, %s)", (no, uraian, anggaran, realisasi, lebih_kurang, tahun_baru))
        
        # Mendapatkan ID dari baris yang baru diinsert
        new_id = g.con.lastrowid
        
        # Commit perubahan
        g.con.connection.commit()
        insert_or_update_urutan(new_id,kategori,tahun_baru)
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/admin/dana/tambah/sub', methods=['POST'])
@jwt_required()
def tambah_sub_dana():
    data = request.json
    tahun_lama, tahun_baru = data.get('tahun_lama'), data.get('tahun_baru')
    kategori, no, uraian, anggaran = data.get("kategori"), data.get('no'), data.get('uraian'), data.get('anggaran')
    realisasi, lebih_kurang, rab = data.get('realisasi'), data.get('lebih_kurang'), data.get('rab')
    parent_id = data.get('parent_id')

    # Debugging input data
    print(f"Input data: {data}")
    print(f"tahun_lama: {tahun_lama}, tahun_baru: {tahun_baru}, kategori: {kategori}, no: {no}, uraian: {uraian}, anggaran: {anggaran}, realisasi: {realisasi}, lebih_kurang: {lebih_kurang}, rab: {rab}, parent_id: {parent_id}")

    # Fungsi untuk insert data ke tabel realisasi
    def insert_data(tahun, rab_val, new_tahun=None):
        query = f"INSERT INTO realisasi_{kategori} (no, uraian, anggaran, realisasi, `lebih/(kurang)`, tahun, rab" + (", jumlah)" if new_tahun else ")") + " VALUES (%s, %s, %s, %s, %s, %s, %s" + (", %s)" if new_tahun else ")")
        params = (no, uraian, anggaran, realisasi, lebih_kurang, tahun, rab_val) + ((new_tahun,) if new_tahun else ())
        
        # Debugging query insert realisasi
        print(f"Insert Query: {query}")
        print(f"Insert Params: {params}")

        g.con.execute(query, params)
        new_id = g.con.lastrowid
        detail = ""

        mysql.connection.commit()
        print(f"New ID after insert: {new_id}")

        if parent_id:
            detail = f"{tahun}-{kategori}-{new_id}"
            update_query = f"UPDATE realisasi_{kategori} SET class = 'hidden-row', detail = %s WHERE id = %s"
            g.con.execute(update_query, (detail, new_id))
            mysql.connection.commit()
            print(f"Updated child row with detail: {detail}")

        return new_id, detail

    # Fungsi untuk update urutan data
    def update_urutan(tahun, new_id, detail):
        g.con.execute(f"SELECT class, onclick FROM realisasi_{kategori} WHERE id = %s", (parent_id,))
        parent = g.con.fetchone()

        # Debugging query hasil
        print(f"Parent data: {parent}")

        if parent_id and parent:
            parent_onclick = parent[1].replace("')", "")
            if parent[1] == '':
                parent_onclick = "toggleDetails('" 
                parent_onclick = f"{parent_onclick}{detail}')"
            else:
                parent_onclick = f"{parent_onclick},{detail}')"
            if parent[0] == "hidden-row":
               parent_class = "hidden-row clickable-row"
            else:
                parent_class = "clickable-row" 
            g.con.execute(f"UPDATE realisasi_{kategori} SET class = %s, onclick = %s WHERE id = %s", (parent_class, parent_onclick, parent_id))
            mysql.connection.commit()
            print(f"Updated parent onclick: {parent_onclick}")

    # Insert data baru
    print(f"Inserting data for tahun: {tahun_baru if rab == 0 else tahun_lama}, rab: {rab}")
    new_id, detail = insert_data(tahun_baru if rab == 0 else tahun_lama, rab, tahun_baru if rab != 0 else None)

    # Update urutan jika diperlukan
    print(f"Updating urutan for new_id: {new_id}, detail: {detail}")
    update_urutan(tahun_baru if rab == 0 else tahun_lama, new_id, detail)

    print(f"Inserting or updating urutan for tahun_baru: {tahun_baru}")
    insert_or_update_urutan(new_id, kategori, tahun_lama, parent_id)

    return jsonify({"msg": "SUKSES"})


@app.route('/admin/dana/edit/id', methods=['PUT'])
@jwt_required()
def edit_id_dana():
    tahun_lama = request.json.get('tahun_lama')
    tahun_baru = request.json.get('tahun_baru')
    kategori = request.json.get("kategori")
    uraian = request.json.get('uraian')
    id = request.json.get("id")
    no = request.json.get('no')
    anggaran = request.json.get('anggaran')
    realisasi = request.json.get('realisasi')
    lebih_kurang = request.json.get('lebih_kurang')
    rab = request.json.get('rab', 0)  # Default ke 0 jika 'rab' tidak ditemukan
    try:
        print(rab)
        if int(rab) == 1:
            lebih_kurang = format_currency(clean_currency(lebih_kurang))
            print(tahun_baru)
            g.con.execute(f"UPDATE realisasi_{kategori} SET no = %s, uraian = %s , anggaran = %s, realisasi = %s, `lebih/(kurang)` = %s , jumlah = %s WHERE id = %s ",(no,uraian,anggaran,realisasi,lebih_kurang,tahun_baru,id))
            mysql.connection.commit()
        else:
            g.con.execute(f"UPDATE realisasi_{kategori} SET no = %s, uraian = %s , anggaran = %s, realisasi = %s, `lebih/(kurang)` = %s , tahun = %s WHERE id = %s ",(no,uraian,anggaran,realisasi,lebih_kurang,tahun_baru,id))
            mysql.connection.commit()
            
            print("jalan 1")
            if tahun_baru != tahun_lama:
                    print("jalan 2")
                    hapus_urutan_lama(id,kategori,tahun_lama)    
                    insert_or_update_urutan(id,kategori,tahun_baru)
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/admin/dana_new/edit/id', methods=['PUT'])
@jwt_required()
def edit_id_dana_new():
    tahun_lama = request.json.get('tahun_lama')
    tahun_baru = request.json.get('tahun_baru') or ''
    kategori = request.json.get("kategori")
    id = request.json.get("id")
    no = request.json.get('no')
    if kategori == 'anggaran':
        uraian = request.json.get('uraian') or ''
        anggaran = request.json.get('anggaran') or ''
        type = request.json.get('type') or ''
        # Menggunakan cursor untuk execute dan rowcount
        print(f"UPDATE tabel_transaksi SET no = {no},  uraian = '{uraian}', anggaran = {anggaran}, type = '{type}', tahun = '{tahun_baru}' WHERE id = {id}")
        g.con.execute(f"UPDATE tabel_anggaran SET no = {no}, uraian = '{uraian}', anggaran = {anggaran}, type = '{type}', tahun = '{tahun_baru}' WHERE id = {id}")
        g.con.connection.commit()
    else:
        tanggal = request.json.get('tanggal')
        keterangan = request.json.get('keterangan')
        nominal = request.json.get('nominal')
        alokasi_lama = request.json.get('alokasi_lama')
        alokasi = request.json.get('alokasi')
        alokasi_parts = alokasi.split("-")
        id_anggaran = alokasi_parts[0]
        alokasi = alokasi_parts[1]
        g.con.execute(f"UPDATE tabel_transaksi SET no = {no}, tanggal = '{tanggal}', keterangan = '{keterangan}', nominal = {nominal}, alokasi= '{alokasi}', tahun = '{tahun_baru}' WHERE id = {id}")
        if alokasi_lama != alokasi:
            g.con.execute(f"UPDATE gabung_anggaran_transaksi SET id_tabel_anggaran = %s WHERE id_transaksi = %s", 
                           (id_anggaran, id,))
        # Commit perubahan
        g.con.connection.commit()
    return jsonify({"msg":"SUKSES"})


@app.route('/admin/edit_dana', methods=['PUT'])
@jwt_required()
def edit_dana():
    id = request.form['id']
    tahun = request.form['tahun']
    dana = request.form['dana']
    digunakan = request.form['digunakan']
    sisah = request.form['sisah']
    try:
        g.con.execute("UPDATE dana SET tahun = %s, dana = %s, keterangan = %s, sisah = %s WHERE id = %s",(tahun,dana,digunakan,sisah,id))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

#hapus
@app.route('/admin/hapus_dana', methods=['DELETE'])
@jwt_required()
def hapus_dana():
    tahun = request.form['tahun']
    tahun = str(tahun)
    if tahun == "semua_tahun":
        try:
            g.con.execute("TRUNCATE `realisasi_belanja`")
            g.con.execute("TRUNCATE `realisasi_pembiayaan`")
            g.con.execute("TRUNCATE `realisasi_pendapatan`")
            mysql.connection.commit()
            return jsonify({"msg":"SUKSES"})
        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        try:
            g.con.execute("DELETE FROM realisasi_pendapatan WHERE tahun = %s", (tahun,))
            g.con.execute("DELETE FROM realisasi_belanja WHERE tahun = %s", (tahun,))
            g.con.execute("DELETE FROM realisasi_pembiayaan WHERE tahun = %s", (tahun,))
            g.con.execute("DELETE FROM urutan WHERE tahun = %s", (tahun,))
            mysql.connection.commit()
            return jsonify({"msg":"SUKSES"})
        except Exception as e:
            print(str(e))
            return jsonify({"error": str(e)})
#hapus
@app.route('/admin/hapus_dana_new', methods=['DELETE'])
@jwt_required()
def hapus_dana_new():
    tahun = request.form['tahun']
    tahun = str(tahun)
    if tahun == "semua_tahun":
        try:
            g.con.execute("TRUNCATE `tabel_anggaran`")
            g.con.execute("TRUNCATE `tabel_transaksi`")
            g.con.execute("TRUNCATE `gabung_anggaran_transaksi`")
            mysql.connection.commit()
            return jsonify({"msg":"SUKSES"})
        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        try:
            g.con.execute("DELETE FROM tabel_anggaran WHERE tahun = %s", (tahun,))
            g.con.execute("DELETE FROM tabel_transaksi WHERE tahun = %s", (tahun,))
            mysql.connection.commit()
            return jsonify({"msg":"SUKSES"})
        except Exception as e:
            print(str(e))
            return jsonify({"error": str(e)})
        

@app.route('/admin/dana/hapus/id', methods=['DELETE'])
@jwt_required()
def ubah_urutadana():
    tahun = request.json.get("year")
    category = request.json.get("category")
    id_ = request.json.get("id")
    try:
        g.con.execute(f"DELETE FROM realisasi_{category} WHERE id = %s ", (id_,))
        mysql.connection.commit()
        hapus_urutan_lama(id_, category, tahun)
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/admin/dana_new/hapus/id', methods=['DELETE'])
@jwt_required()
def hapus_dana_new_id():
    tahun = request.json.get("year")
    category = request.json.get("category")
    id_ = request.json.get("id")
    
    try:
        g.con.execute(f"DELETE FROM tabel_{category} WHERE id = %s ", (id_,))
        mysql.connection.commit()
        hapus_urutan_lama(id_, category, tahun)
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/tambah_dana', methods=['POST'])
@jwt_required()
def tambah_dana():
    filependapatan = request.files['excellpendapatan']
    filebelanja = request.files['excellbelanja']
    filepembiayaan = request.files['excellpembiayaan']
    
    if filependapatan and allowed_file(filependapatan.filename):
        df_pendapatan = pd.read_excel(filependapatan)
        insert_data_from_dataframe(df_pendapatan, "realisasi_pendapatan")
        
    else:
        return jsonify({"error_pendapatan": "File 'excellpendapatan' bukan berkas Excel (.xlsx)"})

    if filebelanja and allowed_file(filebelanja.filename):
        df_belanja = pd.read_excel(filebelanja)
        insert_data_from_dataframe(df_belanja, "realisasi_belanja")
    else:
        return jsonify({"error_belanja": "File 'excellbelanja' bukan berkas Excel (.xlsx)"})

    if filepembiayaan and allowed_file(filepembiayaan.filename):
        df_pembiayaan = pd.read_excel(filepembiayaan)
        insert_data_from_dataframe(df_pembiayaan, "realisasi_pembiayaan")
        thn = df_pembiayaan.iloc[0]['thn']  # Misalnya baris pertama
        sql = "INSERT INTO urutan(tahun) VALUES (%s)"
        g.con.execute(sql, (thn,))
        mysql.connection.commit()
    else:
        return jsonify({"error_pembiayaan": "File 'excellpembiayaan' bukan berkas Excel (.xlsx)"})

    return jsonify({"msg":"SUKSES"})

@app.route('/admin/dana/rab', methods=['POST'])
@jwt_required()
def tambah_rab():
    filerab = request.files['file_rab']
    if filerab and allowed_file(filerab.filename):
        df_rab = pd.read_excel(filerab)
        for index, row in df_rab.iterrows():
            sql = f"INSERT INTO rab (content,kategori , tahun) VALUES (%s, %s, %s,)"
            if row['no'] == 'Z' or row['no'] == 'Y':
                row['no'] = ""
            g.con.execute(sql, (row['no'], row['uraian'], str(format_currency(row['anggaran'])), str(format_currency(row['realisasi'])), str(format_currency(row['lebih/(kurang)'])), row['thn']))
    mysql.connection.commit()
    return "blabla"

@app.route('/admin/dana/summary', methods=['POST'])
@jwt_required()
def tambah_summary():
    summary = request.json.get("summary")
    return "blabla"
   
#geografi
@app.route('/admin/geografi')
def admingeo():
    info_list=fetch_data_and_format("SELECT * FROM wilayah")
    return render_template("admin/geografi.html", info_list=info_list)

@app.route('/admin/tambah_wilayah', methods=['POST'])
@jwt_required()
def adminwilayahtambah():
    form_data = request.form
    fields = ['utara','selatan','timur','barat','luas','sawahteri','sawahhu','pemukiman']
    query = f"INSERT INTO wilayah ({', '.join(fields+['tahun'])}) VALUES ({', '.join(['%s'] * (len(fields)+1))})"
    try: 
        g.con.execute(query, tuple(form_data[field] for field in fields)+(form_data['selected_tahun'],))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/edit_wilayah', methods=['PUT'])
@jwt_required()
def adminwilayahedit():
    form_data = request.form
    fields = ['utara','selatan','timur','barat','luas','sawahteri','sawahhu','pemukiman']
    query = f"UPDATE wilayah SET {' = %s, '.join(fields)} = %s WHERE id=%s"
    try: 
        g.con.execute(query, tuple(form_data[field] for field in fields) + (form_data['id'],))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})  
@app.route('/admin/hapus_wilayah', methods=['DELETE'])
@jwt_required()
def adminwilayahhapus():
    id = request.form['id']
    try:
        g.con.execute("DELETE FROM wilayah WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

#monografi
@app.route('/admin/monografi')
def adminmono():
    info_mono=fetch_data_and_format("SELECT * FROM monografi")
    return render_template("admin/monografi.html", info_mono = info_mono,fields_mono=fields_mono)

@app.route('/admin/tambah_mono', methods=['POST'])
@jwt_required()
def adminmonotambah():
    form_data = request.form
    fields = ['jpenduduk', 'jkk', 'laki', 'perempuan', 'jkkprese', 'jkkseja', 'jkkkaya', 'jkksedang', 'jkkmiskin',
            'petani','peternak','pedagang','tukangkayu','tukangbatu','penjahit','asn','pensiunan','perangkatdesa','jasa_wiraswasta',
            'pengrajinbatik','dll', 'islam', 'kristen', 'protestan', 'katolik', 'hindu', 'budha']
    query = f"INSERT INTO monografi ({', '.join(fields + ['tahun'])}) VALUES ({', '.join(['%s'] * (len(fields) + 1))})"
    try: 
        g.con.execute(query, tuple(form_data[field] for field in fields) + (form_data['selected_tahun'],))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
    
@app.route('/admin/edit_mono', methods=['PUT'])
@jwt_required()
def adminmonoedit():
    form_data = request.form
    fields = ['jpenduduk', 'jkk', 'laki', 'perempuan', 'jkkprese', 'jkkseja', 'jkkkaya', 'jkksedang', 'jkkmiskin',
            'petani','peternak','pedagang','tukangkayu','tukangbatu','penjahit','asn','pensiunan','perangkatdesa','jasa_wiraswasta',
            'pengrajinbatik','dll','islam', 'kristen', 'protestan', 'katolik', 'hindu', 'budha']
    query = f"UPDATE monografi SET {' = %s, '.join(fields)} = %s WHERE tahun=%s"
    try: 
        g.con.execute(query, tuple(form_data[field] for field in fields) + (form_data['selected_tahun'],))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
    
@app.route('/admin/hapus_mono', methods=['DELETE'])
@jwt_required()
def adminmonohapus():
    id = request.form['id']
    try:
        g.con.execute("DELETE FROM monografi WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
#anggota
@app.route('/admin/anggota')
def adminanggota():
    g.con.execute("SELECT nama_jabatan FROM urutan_jabatan_pemerintahan")
    rows = g.con.fetchall()
    urutan_jabatan = [row[0] for row in rows]
    list_info = fetch_data_and_format("SELECT * FROM anggota order by id")
    sorted_list_info = sorted(list_info, key=lambda x: urutan_jabatan.index(x['jabatan']) if x['jabatan'] in urutan_jabatan else len(urutan_jabatan))
    jabatan_unik = set(item['jabatan'] for item in list_info)
    jabatan_urut = sorted(jabatan_unik, key=lambda x: urutan_jabatan.index(x) if x in urutan_jabatan else len(urutan_jabatan))
    return render_template("admin/anggota.html", info_list = sorted_list_info, urutan_jabatan = jabatan_urut)
@app.route('/admin/anggota/ubah_jabatan',methods=["POST"])
@jwt_required()
def anggota_ubah_jabatan():
    try:
        databaru = request.form['data_baru']
        databaru = databaru.split(',')
        g.con.execute("TRUNCATE urutan_jabatan_pemerintahan")
        # Memasukkan data baru ke dalam tabel
        for index, i in enumerate(databaru, start=1):
            g.con.execute("INSERT INTO urutan_jabatan_pemerintahan(id, nama_jabatan) VALUES(%s, %s)", (index, i))
            mysql.connection.commit()  # Melakukan commit setiap kali setelah memasukkan data
            
        #for index, i in enumerate(databaru, start=1):
        #    g.con.execute("UPDATE urutan_jabatan_pemerintahan SET nama_jabatan=%s WHERE id=%s", (i, index))
        #    mysql.connection.commit()  # Melakukan commit setiap kali setelah memperbarui data

        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/tambah_anggota', methods=['POST'])
@jwt_required()
def tambah_anggota():
    form_data = request.form
    fields = ['nama_lengkap','nama_alias', 'jabatan', 'niap', 'ttl', 'agama', 'golongan', 'pendidikan_terakhir', 'nomorsk', 'tanggalsk', 'masa_jabatan', 'status']
    try:
        random_name = do_image("tambah","anggota","")
        query = f"INSERT INTO anggota ({', '.join(fields + ['gambar'])}) VALUES ({', '.join(['%s'] * (len(fields) + 1))})"
        g.con.execute(query, tuple(form_data[field] for field in fields) + (random_name,))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
##edit_anggota
@app.route('/admin/edit_anggota', methods=['PUT'])
def anggota_edit():
    id = request.form['id']
    nama_lengkap = request.form['nama_lengkap']
    nama_alias = request.form['nama_alias']
    jabatan = request.form['jabatan']
    niap = request.form['niap']
    ttl = request.form['ttl']
    agama = request.form['agama']
    golongan = request.form['golongan']
    pendidikan_terakhir = request.form['pendidikan_terakhir']
    nomorsk = request.form['nomorsk']
    tanggalsk = request.form['tanggalsk']
    masa_jabatan = request.form['masa_jabatan']
    status = request.form['status']
    try:
        do_image("edit","anggota",id)
        g.con.execute("UPDATE anggota SET nama_lengkap = %s, nama_alias = %s, jabatan = %s, niap = %s, ttl = %s, agama = %s, golongan = %s, pendidikan_terakhir = %s, nomorsk = %s, tanggalsk = %s, masa_jabatan = %s, status = %s WHERE id = %s",
        (nama_lengkap,nama_alias,jabatan,niap,ttl,agama,golongan,pendidikan_terakhir,nomorsk,tanggalsk,masa_jabatan,status,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
#hapus anggota
@app.route('/hapus_anggota', methods=['DELETE'])
@jwt_required()
def hapus_anggota():
    id = request.form['id']
    try:
        do_image("delete","anggota",id)
        g.con.execute("DELETE FROM anggota WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
    
#Galeri
@app.route('/admin/galeri')
def admindgaleri():
    info_list=fetch_data_and_format("SELECT * FROM galeri order by id DESC")
    return render_template("admin/galeri.html", info_list = info_list)

@app.route('/admin/tambah_galeri', methods=['POST'])
@jwt_required()
def tambah_galeri():
    judul = request.form['judul']
    tanggal = datetime.now().date()
    try:
        random_name = do_image("tambah","galeri","")
        g.con.execute("INSERT INTO galeri (judul, gambar , tanggal) VALUES (%s,%s,%s)",(judul,random_name,tanggal))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/admin/edit_galeri', methods=['PUT'])
@jwt_required()
def galeri_edit():
    id = request.form['id']
    judul = request.form['judul']
    try:
        do_image("edit","galeri",id)
        g.con.execute("UPDATE galeri SET judul = %s WHERE id = %s",(judul,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/hapus_galeri', methods=['DELETE'])
@jwt_required()
def hapus_galeri():
    id = request.form['id']
    try:
        do_image("delete","galeri",id)
        g.con.execute("DELETE FROM galeri WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

#vidio
@app.route('/admin/vidio')
def adminvidio():
    info_list=fetch_data_and_format("SELECT * FROM vidio order by id DESC")
    return render_template("admin/vidio.html", info_list = info_list)

@app.route('/admin/edit_vidio', methods=['PUT'])
@jwt_required()
def vidioedit():
    id = request.form['id']
    vidio = request.form['vidio']
    try:
        g.con.execute("UPDATE vidio SET vidio = %s WHERE id = %s",(vidio,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

# admin agenda 
@app.route('/admin/agenda')
def admin_agenda():
    list_agenda=fetch_data_and_format("SELECT * FROM agenda")
    return render_template('admin/agenda.html',list_agenda=list_agenda)
@app.route('/delete-agenda/<id>',methods=["DELETE"])
@jwt_required()
def agenda_delete(id):
    try:
        do_image("delete","agenda",id)
        g.con.execute("DELETE FROM agenda WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/tambah-agenda',methods=["POST"])
@jwt_required()
def agenda_tambah():
    title = request.form['title']
    jam_mulai = request.form['jam_mulai']
    jam_selesai = request.form['jam_selesai']
    pemimpin_kegiatan = request.form['pemimpin_kegiatan']
    kategori = request.form['kategori']
    keterangan = request.form['keterangan']
    try:
        random_name = do_image("tambah","agenda","")
        g.con.execute("INSERT INTO agenda(title, start, end, kategori, pemimpin_kegiatan, keterangan, gambar) VALUES(%s, %s, %s, %s, %s, %s, %s)", (title, jam_mulai, jam_selesai, kategori, pemimpin_kegiatan, keterangan, random_name))
        mysql.connection.commit()  
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/edit-agenda',methods=["PUT"])
@jwt_required()
def agenda_edit():
    id = request.form['id']
    title = request.form['title']
    jam_mulai = request.form['jam_mulai']
    jam_selesai = request.form['jam_selesai']
    pemimpin_kegiatan = request.form['pemimpin_kegiatan']
    keterangan = request.form['keterangan']
    kategori = request.form['kategori']
    try:
        do_image("edit","agenda",id)
        g.con.execute("UPDATE agenda SET title = %s, start = %s, end = %s, kategori = %s, pemimpin_kegiatan = %s, keterangan = %s WHERE id = %s",(title,jam_mulai,jam_selesai,kategori,pemimpin_kegiatan,keterangan,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
#halaman bpd
@app.route('/admin/bpd')
def admin_bpd():
    g.con.execute("SELECT nama_jabatan FROM urutan_jabatan")
    rows = g.con.fetchall()
    urutan_jabatan = [row[0] for row in rows]
    list_info = fetch_data_and_format("SELECT * FROM bpd")
    sorted_list_info = sorted(list_info, key=lambda x: urutan_jabatan.index(x['jabatan']) if x['jabatan'] in urutan_jabatan else len(urutan_jabatan))
    jabatan_unik = set(item['jabatan'] for item in list_info)
    jabatan_urut = sorted(jabatan_unik, key=lambda x: urutan_jabatan.index(x) if x in urutan_jabatan else len(urutan_jabatan))
    return render_template('admin/bpd.html', list_info=sorted_list_info, urutan_jabatan = jabatan_urut)
@app.route('/admin/delete-bpd',methods=["DELETE"])
@jwt_required()
def bpd_delete():
    id = request.form['id']
    try:
        do_image("delete","bpd",id)
        g.con.execute("DELETE FROM bpd WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/tambah-bpd',methods=["POST"])
@jwt_required()
def bpd_tambah():
    nama = request.form['nama']
    jabatan = request.form['jabatan']
    status = request.form['status']
    try:
        random_name = do_image("tambah","bpd","")
        g.con.execute("INSERT INTO bpd(nama, jabatan,status,gambar) VALUES(%s, %s, %s, %s)", (nama, jabatan, status,random_name))
        mysql.connection.commit() 
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/bpd/ubah_jabatan',methods=["POST"])
@jwt_required()
def bpd_ubah_jabatan():
    try:
        databaru = request.form['data_baru']
        databaru = databaru.split(',')
        g.con.execute("TRUNCATE urutan_jabatan")
        for index, i in enumerate(databaru, start=1):
            g.con.execute("INSERT INTO urutan_jabatan_pemerintahan(id, nama_jabatan) VALUES(%s, %s)", (index, i))
            mysql.connection.commit()  # Melakukan commit setiap kali setelah memasukkan data
            
        #for index, i in enumerate(databaru, start=1):
        #    g.con.execute("UPDATE urutan_jabatan_pemerintahan SET nama_jabatan=%s WHERE id=%s", (i, index))
        #    mysql.connection.commit()  # Melakukan commit setiap kali setelah memperbarui data

        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})
@app.route('/admin/edit-bpd',methods=["PUT"])
@jwt_required()
def bpd_edit():
    id = request.form['id']
    nama = request.form['nama']
    jabatan = request.form['jabatan']
    status = request.form['status']
    try:
        do_image("edit","bpd",id)
        g.con.execute("UPDATE bpd SET nama = %s, jabatan = %s, status = %s WHERE id = %s",(nama,jabatan,status,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/admin/tambah_Nota', methods=['POST'])
@jwt_required()
def tambah_Nota():
    judul = request.form['judul']
    link = '_'.join(filter(None, [judul.replace("#", "").replace("?", "").replace("/", "").replace(" ", "_")]))
    id_transaksi = request.form['id_transaksi']
    try: 
        random_name = do_image("tambah","nota","")
        g.con.execute("INSERT INTO nota (judul, gambar, link , id_transaksi ) VALUES (%s,%s,%s,%s)",(judul,random_name,link,id_transaksi))
        mysql.connection.commit()
        return jsonify({"msg":"SUKSES"})
    except Exception as e:
        str(e)
        return jsonify({"error": str(e)})
@app.route('/admin/edit_Nota', methods=['PUT'])
@jwt_required()
def Nota_edit():
    id = request.form['id']
    judul = request.form['judul']
    link = '_'.join(filter(None, [judul.replace("#", "").replace("?", "").replace("/", "").replace(" ", "_")]))
    try:
        status = do_image("edit","nota",id)
        g.con.execute("UPDATE nota SET judul = %s, link = %s  WHERE id = %s",(judul,link,id))
        mysql.connection.commit()
        return jsonify({"msg" : "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})

@app.route('/admin/hapus_Nota', methods=['DELETE'])
@jwt_required()
def hapus_Nota():
    id = request.form['id']
    try:
        do_image("delete","nota",id)
        g.con.execute("DELETE FROM nota WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({"msg": "SUKSES"})
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)})