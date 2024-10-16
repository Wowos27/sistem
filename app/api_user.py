from . import app,mysql,db
from flask import render_template, request, jsonify, redirect, url_for,session,g
import pandas as pd
from PIL import Image
from io import BytesIO
import os,textwrap, locale, json, uuid, time
from datetime import datetime

@app.before_request
def before_request():
    g.con = mysql.connection.cursor()
@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'con'):
        g.con.close()
def fetch_data_and_format(query):
    g.con.execute(query)
    data = g.con.fetchall()
    column_names = [desc[0] for desc in g.con.description]
    info_list = [dict(zip(column_names, row)) for row in data]
    return info_list
def fetch_years(query):
    g.con.execute(query)
    data_thn = g.con.fetchall()
    thn = [{'tahun': str(sistem[0])} for sistem in data_thn]
    return thn
#halaman homepage
@app.route('/')
def homepahe():
    thn_dana_list =fetch_data_and_format("SELECT tahun FROM tabel_anggaran group by tahun")
    session['list_thn_dana']= thn_dana_list 
    return render_template('index.html')
@app.route('/news')
def userberita():
    berita = fetch_data_and_format("SELECT * FROM berita order by id DESC")
    return render_template('homepage.html',info_list = berita)
#halaman berita
@app.route('/berita/<link>')
def detail_berita(link):
    query = "SELECT * FROM berita where link = '"+ str(link) +"' order by id DESC "
    berita = fetch_data_and_format(query)
    return render_template('detail_berita.html',info_list = berita)
#halaman nota
@app.route('/nota/<link>')
def detail_nota(link):
    query = "SELECT * FROM berita where link = '"+ str(link) +"' order by id DESC "
    berita = fetch_data_and_format(query)
    return render_template('detail_nota.html',info_list = berita)
#halaman sejarah
@app.route('/sejarah')
def sejarah():
    g.con.execute("SELECT * FROM sejarah_desa")
    sejarah = g.con.fetchall()
    info_list = []
    for sistem in sejarah:
        list_data = {
            'id': str(sistem[0]),
            'sejarah': str(sistem[1])
        }
        info_list.append(list_data)
    return render_template("sejarah.html", info_list = info_list)

#halaman vidio
@app.route('/video')
def vidio():
    g.con.execute("SELECT * FROM vidio order by id DESC")
    berita = g.con.fetchall()
    info_list = []
    for sistem in berita:
        list_data = {
            'id': str(sistem[0]),
            'vidio': str(sistem[1])        
        }
        info_list.append(list_data)
    return render_template("video.html", info_list = info_list)

#halaman visi misi
@app.route('/visi_misi')
def visi_misi():
    g.con.execute("SELECT * FROM sejarah_desa")
    sejarah = g.con.fetchall()
    info_list = []
    for sistem in sejarah:
        list_data = {
            'id': str(sistem[0]),
            'visi': str(sistem[2]),
            'misi': sistem[3],
        }
        info_list.append(list_data)
    return render_template("visimisi.html", info_list = info_list)

#halaman pemerintahan
@app.route('/pemerintahan_desa')
def pemerintahan_desa():
    g.con.execute("SELECT * FROM anggota order by id")
    anggota = g.con.fetchall()
    column_names = [desc[0] for desc in g.con.description]
    info_list = [dict(zip(column_names, row)) for row in anggota]
    return render_template("pemerintahan_desa.html", info_list = info_list)

#halaman badan desa
@app.route('/badan_desa')
def badan_desa():
    return jsonify({"msg":"under maintance"}),404

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

def set_urutan(column, year):
    urutan = {}
    g.con.execute(f"SELECT {column} FROM urutan WHERE tahun = %s", (year,))
    result= g.con.fetchone()
    if result:
        try:
            urutan.update(json.loads(str(result[0]).replace("'", '"')))
        except json.JSONDecodeError:
            print("Error: Hasil bukan JSON yang valid:", result)
    return urutan if urutan else set_urutan_default(column)
#halaman dana
@app.route('/dana_old/<thn>')
def dana_desa_old(thn):
    info_list = fetch_data_and_format(f"SELECT * FROM realisasi_pendapatan where tahun = {thn} ORDER BY id")
    info_list2 = fetch_data_and_format(f"SELECT * FROM realisasi_belanja where tahun = {thn} ORDER BY id")
    info_list3 = fetch_data_and_format(f"SELECT * FROM realisasi_pembiayaan where tahun = {thn} ORDER BY id")
    return render_template("dana.html", info_list=info_list, info_list2=info_list2, info_list3=info_list3, tahun=thn,  
                           urutan_pendapatan=set_urutan("pendapatan", thn), 
                           urutan_belanja=set_urutan("belanja", thn), 
                           urutan_pembiayaan=set_urutan("pembiayaan", thn))
def format_currency(value):
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
    return locale.currency(value, grouping=True, symbol='Rp')
@app.route('/dana/<thn>')
def dana_desa(thn):
 # Mengambil data dari tabel
    info_list = fetch_data_and_format("SELECT * FROM tabel_anggaran ORDER BY no")
    info_list2 = fetch_data_and_format("SELECT * FROM tabel_transaksi ORDER BY no")
    gabung = fetch_data_and_format("SELECT * FROM gabung_anggaran_transaksi")
    info_list3 = [{**j, 
                    'realisasi': (realisasi := sum( int(k['nominal']) for i in gabung if i['id_tabel_anggaran'] == j['id'] for k in info_list2 if i['id_transaksi'] == k['id'] )),
                    'lebih_kurang': int(j['anggaran']) - realisasi} for j in info_list ]
    gabung_nota = fetch_data_and_format("SELECT * FROM gabung_tabel_transaksi_nota")
    summary = []
    pendapatan = [k for k in info_list3 if k['tahun'] == thn and k['type'] == "pendapatan"]
    pengeluaran = [k for k in info_list3 if k['tahun'] == thn and k['type'] == "pengeluaran"]
    item = {
        'tahun': thn,
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
    return render_template("dana_new.html", info_list=info_list, info_list2=info_list2, info_list3=info_list3, tahun=thn, summary=summary, list_nota = list_nota)

#halaman monografi
@app.route('/monografi')
def mono():
    g.con.execute("SELECT * FROM monografi")
    mono = g.con.fetchall()
    column_names = [desc[0] for desc in g.con.description]
    info_list = [dict(zip(column_names, row)) for row in mono]
    return render_template("user_data_desa/monografi.html", info_list = info_list)
#Halaman geografi
@app.route('/geografi')
def geo():
    g.con.execute("SELECT * FROM wilayah")
    wilayah = g.con.fetchall()
    column_names = [desc[0] for desc in g.con.description]
    info_list = [dict(zip(column_names, row)) for row in wilayah]
    return render_template("user_data_desa/geografi.html", info_list=info_list )

#halaman user galeri
@app.route('/galeri')
def galeri():
    g.con.execute("SELECT * FROM galeri order by id DESC")
    berita = g.con.fetchall()
    info_list = []
    for sistem in berita:
        list_data = {
            'id': str(sistem[0]),
            'judul': str(sistem[1]),
            'gambar': str(sistem[2]),
            'tanggal': str(sistem[3])
        }
        info_list.append(list_data)
    return render_template("/galeri.html", info_list = info_list)
#halaman user galeri
@app.route('/agenda')
def agenda():
    list_agenda=fetch_data_and_format("SELECT * FROM agenda")
    return render_template('agenda.html',list_agenda=list_agenda) 
#get info
@app.route('/info', methods=['GET'])
def get_info():
    g.con.execute("SELECT * FROM sejarah_desa")
    sejarah = g.con.fetchall()
    info_list = []
    for sistem in sejarah:
        list_data = {
            'id': str(sistem[0]),
            'sejarah': str(sistem[1]),
            'visi': str(sistem[2]),
            'misi': str(sistem[3])
        }
        info_list.append(list_data)
    return jsonify(info_list)

#get fasilitas
@app.route('/fasilitas', methods=['GET'])
def get_fasilitas():
    g.con.execute("SELECT * FROM fasilitas")
    sejarah = g.con.fetchall()
    info_list = []
    for sistem in sejarah:
        list_data = {
            'id': str(sistem[0]),
            'fasilitas': str(sistem[1]),
            'kondisi': str(sistem[2])
        }
        info_list.append(list_data)
    return jsonify(info_list)

#get
@app.route('/surat', methods=['GET'])
def get_surat():
    g.con.execute("SELECT * FROM surat")
    surat = g.con.fetchall()
    info_list = []
    for sistem in surat:
        list_data = {
            'id': str(sistem[0]),
            'nama': str(sistem[1]),
            'hp': str(sistem[2]),
            'keterangan': str(sistem[3])
        }
        info_list.append(list_data)
    return jsonify(info_list)

@app.route('/tambah_surat', methods=['POST'])
def tambah_surat():
    nama = request.form['nama']
    hp = request.form['hp']
    keterangan = request.form['keterangan']
    g.con.execute("INSERT INTO surat (nama , hp, keterangan) VALUES (%s,%s,%s)",(nama,hp,keterangan))
    mysql.connection.commit()
    return jsonify({"msg":"SUKSES"})

@app.route('/edit_surat', methods=['POST'])
def edit_surat():
    id = request.form['id']
    nama = request.form['nama']
    hp = request.form['hp']
    keterangan = request.form['keterangan']
    g.con.execute("UPDATE surat SET nama = %s, hp = %s, keterangan = %s WHERE id = %s",(nama,hp,keterangan,id))
    mysql.connection.commit()
    return jsonify({"msg":"SUKSES"})

@app.route('/hapus_surat', methods=['POST'])
def hapus_surat():
    id = request.form['id']
    g.con.execute("DELETE FROM surat WHERE id = %s",(id))
    mysql.connection.commit()
    return jsonify({"msg":"SUKSES"})
#halaman bpd
@app.route('/bpd')
def bpd():
    g.con.execute("SELECT nama_jabatan FROM urutan_jabatan")
    rows = g.con.fetchall()
    urutan_jabatan = [row[0] for row in rows]
    list_info = fetch_data_and_format("SELECT * FROM bpd")
    sorted_list_info = sorted(list_info, key=lambda x: urutan_jabatan.index(x['jabatan']) if x['jabatan'] in urutan_jabatan else len(urutan_jabatan))
    return render_template('bpd.html', list_info=sorted_list_info)
@app.route('/coba_excell')
def coba_excell():
    return render_template('coba_excell.html')