import os
from os.path import join, dirname
from dotenv import load_dotenv

from pymongo import MongoClient
import jwt #pip install pyjwt 
from datetime import datetime, timedelta 
import hashlib #untuk enkripsi, sudah bawaan
from flask import (
    Flask, 
    render_template, 
    jsonify, 
    request,
    redirect, 
    url_for )
from werkzeug.utils import secure_filename
from bson import ObjectId



dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY = os.environ.get("TOKEN_KEY")

client = MongoClient(MONGODB_URI)

db = client[DB_NAME]

app = Flask(__name__)

# app.config['TEMPLATES_AUTO_RELOAD']=True
app.config['UPLOAD_FOLDER']='./static/gunung_pics'

@app.route('/', methods=['GET']) #UNTUK HALAMAN INDEX
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    print("Received token:", token_receive)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' :payload.get('useremail')})
        user_role = user_info['role']
        return render_template('index.html', user_role = user_role)
    except jwt.ExpiredSignatureError:
        msg = 'Your token has expired'
        return redirect(url_for('halaman_login',msg = msg))
    except jwt.exceptions.DecodeError:
        msg = 'There was a problem logging you in'
        return redirect(url_for('halaman_login',msg = msg))

@app.route('/halaman_login', methods=['GET']) #UNTUK HALAMAN LOGIN
def halaman_login():
    msg = request.args.get('msg')
    return render_template('login.html', msg =msg)
    
@app.route("/sign_in", methods=["POST"]) #UNTUK HALAMAN LOGIN
def sign_in():
    useremail_receive = request.form["useremail_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
        {
            "useremail": useremail_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "useremail": useremail_receive,
            # the token will be valid for 24 hours
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "Email atau Password anda tidak sesuai",
            }
        )

@app.route('/halaman_signup', methods=['GET']) #UNTUK HALAMAN SIGNUP
def halaman_signup():
    return render_template('signup.html')

@app.route("/sign_up/save", methods=["POST"]) #UNTUK HALAMAN SIGNUP
def sign_up():
    useremail_receive = request.form['useremail_give']
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "useremail" : useremail_receive,
        "username"  : username_receive,
        "password"  : password_hash,
        "role"      : "user"
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_email', methods=['POST'])  #UNTUK HALAMAN SIGNUP
def check_dup():
    useremail_receive = request.form['useremail_give']
    exists = bool(db.users.find_one({"useremail": useremail_receive}))
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/halaman_tambah', methods=['GET']) #UNTUK HALAMAN TAMBAH
def halaman_tambah():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        return render_template('tambah.html')
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/tambah_gunung', methods=['POST']) #UNTUK HALAMAN TAMBAH
def posting():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        #di browser client, buat kondisi input tidak boleh kosong, termasuk input choose file
        name_receive = request.form.get('name_give')
        provinsi_receive = request.form.get('provinsi_give')
        ketinggian_receive = request.form.get('ketinggian_give')
        gmaps_receive = request.form.get('gmaps_give')
        iframe_receive = request.form.get('iframe_give')
        deskripsiUmum_receive = request.form.get('deskripsiUmum_give')
        deskripsiPerlengkapan_receive = request.form.get('deskripsiPerlengkapan_give')
        deskripsiPeringatan_receive = request.form.get('deskripsiPeringatan_give')

        if 'file_give' in request.files:
            file = request.files.get('file_give')
            file_name = secure_filename(file.filename)
            picture_name= file_name.split(".")[0]
            ekstensi = file_name.split(".")[1]
            picture_name = f"{picture_name}[{name_receive}].{ekstensi}"
            file_path = f'./static/gunung_pics/{picture_name}'
            file.save(file_path)
        else: picture_name =f"default.jpg"

        doc = {
            'nama_gunung' : name_receive,
            'provinsi_gunung' : provinsi_receive,
            'ketinggian_gunung' : ketinggian_receive,
            'gambar_gunung' : picture_name,
            'link_gmaps' : gmaps_receive,
            'link_iframe' : iframe_receive,
            'deskripsi_umum' : deskripsiUmum_receive,
            'deskripsi_perlengkapan' : deskripsiPerlengkapan_receive,
            'deskripsi_peringatan' : deskripsiPeringatan_receive,
        }
        db.gunung.insert_one(doc)
        return jsonify({
            'result' : 'success',
            'msg' : 'Konten baru telah ditambahkan!'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/getListGunung', methods=['GET']) #UNTUK HALAMAN INDEX DAN SEARCH DI GAGAL CARI
def get_gunung():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        kategori = request.args.get('kategori')
        print(kategori)
        if kategori== 'default':
            print('default')
            list_gunung = list(db.gunung.find({}))
            for gunung in list_gunung:
                gunung['_id'] = str(gunung['_id'])
                gunung['likes'] = db.likes.count_documents({
                    'id_gunung' : gunung['_id']
                })
            return jsonify({'result':'success', 'list_gunung' : list_gunung})
        
        elif kategori == 'favorit':
            print('favorit')
            list_gunung = list(db.gunung.find({}))
            for gunung in list_gunung:
                gunung['_id'] = str(gunung['_id'])
                gunung['likes'] = db.likes.count_documents({
                    'id_gunung' : gunung['_id']
                })
            #sorted untuk membuat list favorit berdasarkan likes terbanyak
            list_favorit = sorted(list_gunung, key=lambda x: x['likes'], reverse=True)
            #filter dokumen yang memiliki 0 likes
            filtered_list = [gunung for gunung in list_favorit if gunung["likes"] != 0]
            if len(filtered_list) == 0:
                return jsonify({'result':'list_kosong'})

            return jsonify({'result':'success', 'list_gunung' : filtered_list})
        
        else :
            keyword = kategori
            print('search')
            list_search1 = list(db.gunung.find({'nama_gunung' : {'$regex' : keyword ,'$options' : 'i'}}))
            list_search2 = list(db.gunung.find({'provinsi_gunung' : {'$regex' : keyword ,'$options' : 'i'}}))

            if list_search1 : 
                hasil_pencarian = list_search1
                for item in hasil_pencarian: 
                    item['_id'] = str(item['_id'])
                    item['likes'] = db.likes.count_documents({
                        'id_gunung' : item['_id']
                    })
                return jsonify({'result':'success', 'list_gunung' : hasil_pencarian})
            elif list_search2 : 
                hasil_pencarian = list_search2
                for item in hasil_pencarian: 
                    item['_id'] = str(item['_id'])
                    item['likes'] = db.likes.count_documents({
                        'id_gunung' : item['_id']
                    })
                return jsonify({'result':'success', 'list_gunung' : hasil_pencarian})
            else : 
                return jsonify({'result':'gagal_cari'})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/halaman_gagal', methods=['GET'])
def gagal_cari():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        return render_template('gagal_cari.html')
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/search', methods=['GET'])
def search():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        keyword = request.args.get('keyword')
        user_info = db.users.find_one({'useremail' :payload.get('useremail')})
        user_role = user_info['role']
        return render_template('index.html', user_role = user_role, keyword = keyword)
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/halaman_edit/<id_gunung>', methods=['GET']) #UNTUK HALAMAN EDIT, id gunung dibawa dengan dinamic route
def halaman_edit(id_gunung):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        id_gunung = ObjectId(id_gunung)
        info_gunung = db.gunung.find_one({'_id' : id_gunung})
        info_gunung["_id"] = str(info_gunung["_id"])
        return render_template('edit.html', info_gunung=info_gunung)
    
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/edit_gunung', methods=['POST'])  #UNTUK HALAMAN EDIT
def edit():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        id_gunung = request.form.get('id_gunung_give')
        id_gunung = ObjectId(id_gunung)

        name_receive = request.form.get('name_give')
        provinsi_receive = request.form.get('provinsi_give')
        ketinggian_receive = request.form.get('ketinggian_give')
        gmaps_receive = request.form.get('gmaps_give')
        iframe_receive = request.form.get('iframe_give')
        deskripsiUmum_receive = request.form.get('deskripsiUmum_give')
        deskripsiPerlengkapan_receive = request.form.get('deskripsiPerlengkapan_give')
        deskripsiPeringatan_receive = request.form.get('deskripsiPeringatan_give')

        if 'file_give' in request.files:
            data_lama = db.gunung.find_one({'_id' : id_gunung})
            gambar_lama = data_lama['gambar_gunung']
            if gambar_lama != "default.jpg" :
                os.remove(f'./static/gunung_pics/{gambar_lama}') #hapus gambar lama di server biar ga jadi sampah

            file = request.files.get('file_give')
            file_name = secure_filename(file.filename)
            picture_name= file_name.split(".")[0]
            ekstensi = file_name.split(".")[1]
            picture_name = f"{picture_name}[{name_receive}].{ekstensi}"
            file_path = f'./static/gunung_pics/{picture_name}'
            file.save(file_path)

            doc = {
                'nama_gunung' : name_receive,
                'provinsi_gunung' : provinsi_receive,
                'ketinggian_gunung' : ketinggian_receive,
                'gambar_gunung' : picture_name,
                'link_gmaps' : gmaps_receive,
                'link_iframe' : iframe_receive,
                'deskripsi_umum' : deskripsiUmum_receive,
                'deskripsi_perlengkapan' : deskripsiPerlengkapan_receive,
                'deskripsi_peringatan' : deskripsiPeringatan_receive,
            }

        else :
            doc = {
                'nama_gunung' : name_receive,
                'provinsi_gunung' : provinsi_receive,
                'ketinggian_gunung' : ketinggian_receive,
                'link_gmaps' : gmaps_receive,
                'link_iframe' : iframe_receive,
                'deskripsi_umum' : deskripsiUmum_receive,
                'deskripsi_perlengkapan' : deskripsiPerlengkapan_receive,
                'deskripsi_peringatan' : deskripsiPeringatan_receive,
            }
        db.gunung.update_one({'_id' : id_gunung},{'$set': doc})
        return jsonify({
            'result' : 'success',
            'msg' : 'Data berhasil diedit'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/delete_gunung', methods=['POST'])  #UNTUK HALAMAN DELETE
def delete_gunung():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        id_gunung = request.form.get('id_gunung_give')
        id_gunung = ObjectId(id_gunung)
        info_gunung = db.gunung.find_one({'_id' : id_gunung})
        gambar_gunung = info_gunung['gambar_gunung']
        if gambar_gunung != "default.jpg":
            os.remove(f'./static/gunung_pics/{gambar_gunung}') #hapus gambar lama di server biar ga jadi sampah
        db.gunung.delete_one({'_id' : id_gunung})
        id_gunung = str(id_gunung)  #hapus likes dan komen pada gunungnya juga di database
        db.likes.delete_many({'id_gunung': id_gunung})
        db.komentar.delete_many({'id_gunung': id_gunung})
        return jsonify({ 'result' : 'success' , 'msg' : 'Data gunung berhasil dihapus'})

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))


@app.route('/detail/<id_gunung>', methods=['GET']) #UNTUK HALAMAN DETAIL, id gunung dibawa dengan dinamic route
def detail_gunung(id_gunung):
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})
        id_gunung = ObjectId(id_gunung)
        info_gunung = db.gunung.find_one({'_id' : id_gunung})
        id_gunung = str(id_gunung)
        komentar_gunung = list(db.komentar.find({'id_gunung' : id_gunung}).sort('tanggal', -1).limit(10))
        for komentar in komentar_gunung:
            komentar['tanggal'] = komentar['tanggal'].split('-')[0]
        jumlah_komentar = len(komentar_gunung)
        
        # db.likes.insert_one({
        #     'id_gunung' : id_gunung,
        #     'useremail' : payload.get('useremail')            
        # })
        like =bool(db.likes.find_one({
            'id_gunung' : id_gunung,
            'useremail' : payload.get('useremail')            
        }))
        like= str(like)
        return render_template('detail.html', 
                               info_gunung=info_gunung, 
                               komentar_gunung=komentar_gunung, 
                               jumlah_komentar=jumlah_komentar, 
                               like=like)

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/komentar', methods=['POST'])  #UNTUK HALAMAN DETAIL
def tambah_komentar():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})

        id_gunung = request.form.get('id_gunung_give')
        useremail = user_info['useremail']
        username = user_info['username']
        komentar_receive = request.form.get('komentar_give')

        doc = {
            'id_gunung' : id_gunung,
            'useremail' : useremail,
            'username' : username,
            'komentar': komentar_receive,
            'tanggal' : datetime.now().strftime('%d/%m/%Y-%H:%M:%S')
        }
        db.komentar.insert_one(doc)
        return jsonify({ 'result' : 'success' , 'msg' : 'Berhasil menambahkan komentar'})

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))


@app.route('/update_like', methods=['POST'])   #UNTUK HALAMAN DETAIL
def update_like():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})
        id_gunung = request.form.get('id_gunung_give')
        action_receive = request.form.get('action_give')
        doc = {
            'id_gunung' : id_gunung,
            'useremail' : user_info.get('useremail')
        }
        if action_receive == 'like' :
            db.likes.insert_one(doc)
        else : db.likes.delete_one(doc)

        return jsonify({
            'result' : 'success',
            'msg' : 'Updated!',
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

def replace_characters(text):
    text = text.replace('\n', '\\n')
    
    text = text.replace('\r', '\\r')

    text = text.replace('\t', '\\t')

    return text

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)