from pyobigram.utils import sizeof_fmt,get_file_size,createID,nice_time
from pyobigram.client import ObigramClient,inlineQueryResultArticle
from MoodleClient import MoodleClient

from JDatabase import JsonDatabase
import zipfile
import os
import infos
import xdlink
import mediafire
#from megacli.mega import Mega
#import megacli.megafolder as megaf
#import megacli.mega
import datetime
import time
import youtube
import NexCloudClient

from pydownloader.downloader import Downloader
from ProxyCloud import ProxyCloud
import ProxyCloud
import socket
import S5Crypto
import threading

def downloadFile(downloader,filename,currentBits,totalBits,speed,time,args):
    try:
        bot = args[0]
        message = args[1]
        thread = args[2]
        if thread.getStore('stop'):
            downloader.stop()
        downloadingInfo = infos.createDownloading(filename,totalBits,currentBits,speed,time,tid=thread.id)
        bot.editMessageText(message,downloadingInfo)
    except Exception as ex: print(str(ex))
    pass

def uploadFile(filename,currentBits,totalBits,speed,time,args):
    try:
        bot = args[0]
        message = args[1]
        originalfile = args[2]
        thread = args[3]
        downloadingInfo = infos.createUploading(filename,totalBits,currentBits,speed,time,originalfile)
        bot.editMessageText(message,downloadingInfo)
    except Exception as ex: print(str(ex))
    pass

def processUploadFiles(filename,filesize,files,update,bot,message,thread=None,jdb=None):
    try:
        bot.editMessageText(message,'<b>🔄 Preparando para subir...</b>')
        evidence = None
        fileid = None
        user_info = jdb.get_user(update.message.sender.username)
        cloudtype = user_info['cloudtype']
        proxy = ProxyCloud.parse(user_info['proxy'])
        if cloudtype == 'moodle':
            client = MoodleClient(user_info['moodle_user'],
                                  user_info['moodle_password'],
                                  user_info['moodle_host'],
                                  user_info['moodle_repo_id'],
                                  proxy=proxy)
            loged = client.login()
            itererr = 0
            if loged:
                if user_info['uploadtype'] == 'evidence':
                    evidences = client.getEvidences()
                    evidname = str(filename).split('.')[0]
                    for evid in evidences:
                        if evid['name'] == evidname:
                            evidence = evid
                            break
                    if evidence is None:
                        evidence = client.createEvidence(evidname)

                originalfile = ''
                if len(files)>1:
                    originalfile = filename
                draftlist = []
                for f in files:
                    f_size = get_file_size(f)
                    resp = None
                    iter = 0
                    tokenize = False
                    if user_info['tokenize']!=0:
                       tokenize = True
                    while resp is None:
                          if user_info['uploadtype'] == 'evidence':
                             fileid,resp = client.upload_file(f,evidence,fileid,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                             draftlist.append(resp)
                          if user_info['uploadtype'] == 'draft':
                             fileid,resp = client.upload_file_draft(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                             draftlist.append(resp)
                          if user_info['uploadtype'] == 'blog':
                             fileid,resp = client.upload_file_blog(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                             draftlist.append(resp)
                          if user_info['uploadtype'] == 'calendario':
                             fileid,resp = client.upload_file_calendar(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                             draftlist.append(resp)
                          iter += 1
                          if iter>=10:
                              break
                    os.unlink(f)
                if user_info['uploadtype'] == 'evidence':
                    try:
                        client.saveEvidence(evidence)
                    except:pass
                return draftlist
            else:
                bot.editMessageText(message,'<b>❌ Error en la plataforma</b>')
        elif cloudtype == 'cloud':
            tokenize = False
            if user_info['tokenize']!=0:
               tokenize = True
            bot.editMessageText(message,'<b>☁️ Subiendo archivo...</b>')
            host = user_info['moodle_host']
            user = user_info['moodle_user']
            passw = user_info['moodle_password']
            remotepath = user_info['dir']
            client = NexCloudClient.NexCloudClient(user,passw,host,proxy=proxy)
            loged = client.login()
            if loged:
               originalfile = ''
               if len(files)>1:
                    originalfile = filename
               filesdata = []
               for f in files:
                   data = client.upload_file(f,path=remotepath,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                   filesdata.append(data)
                   os.unlink(f)
               return filesdata
        return None
    except Exception as ex:
        bot.editMessageText(message,f'<b>❌ Error</b>\n<code>{str(ex)}</code>')
        return None


def processFile(update,bot,message,file,thread=None,jdb=None):
    file_size = get_file_size(file)
    getUser = jdb.get_user(update.message.sender.username)
    max_file_size = 1024 * 1024 * getUser['zips']
    file_upload_count = 0
    client = None
    findex = 0
    if file_size > max_file_size:
        compresingInfo = infos.createCompresing(file,file_size,max_file_size)
        bot.editMessageText(message,compresingInfo)
        zipname = str(file).split('.')[0] + createID()
        mult_file = zipfile.MultiFile(zipname,max_file_size)
        zip = zipfile.ZipFile(mult_file,  mode='w', compression=zipfile.ZIP_DEFLATED)
        zip.write(file)
        zip.close()
        mult_file.close()
        client = processUploadFiles(file,file_size,mult_file.files,update,bot,message,jdb=jdb)
        try:
            os.unlink(file)
        except:pass
        file_upload_count = len(zipfile.files)
    else:
        client = processUploadFiles(file,file_size,[file],update,bot,message,jdb=jdb)
        file_upload_count = 1
    bot.editMessageText(message,'<b>📄 Preparando archivo...</b>')
    evidname = ''
    files = []
    if client:
        if getUser['cloudtype'] == 'moodle':
            if getUser['uploadtype'] == 'evidence':
                try:
                    evidname = str(file).split('.')[0]
                    txtname = evidname + '.txt'
                    evidences = client.getEvidences()
                    for ev in evidences:
                        if ev['name'] == evidname:
                           files = ev['files']
                           break
                        if len(ev['files'])>0:
                           findex+=1
                    client.logout()
                except:pass
            if getUser['uploadtype'] == 'draft' or getUser['uploadtype'] == 'blog' or getUser['uploadtype']=='calendario':
               for draft in client:
                   files.append({'name':draft['file'],'directurl':draft['url']})
        else:
            for data in client:
                files.append({'name':data['name'],'directurl':data['url']})

        # MODIFICAR ENLACES para que tengan /webservice
        for i in range(len(files)):
            url = files[i]['directurl']
            if 'aulacened.uci.cu' in url:
                files[i]['directurl'] = url.replace('://aulacened.uci.cu/', '://aulacened.uci.cu/webservice/')

        bot.deleteMessage(message.chat.id,message.message_id)
        finishInfo = infos.createFinishUploading(file,file_size,max_file_size,file_upload_count,file_upload_count,findex)
        filesInfo = infos.createFileMsg(file,files)
        bot.sendMessage(message.chat.id,finishInfo+'\n'+filesInfo,parse_mode='html')
        if len(files)>0:
            txtname = str(file).split('/')[-1].split('.')[0] + '.txt'
            sendTxt(txtname,files,update,bot)

def ddl(update,bot,message,url,file_name='',thread=None,jdb=None):
    downloader = Downloader()
    file = downloader.download_url(url,progressfunc=downloadFile,args=(bot,message,thread))
    if not downloader.stoping:
        if file:
            processFile(update,bot,message,file,jdb=jdb)
        else:
            megadl(update,bot,message,url,file_name,thread,jdb=jdb)

def megadl(update,bot,message,megaurl,file_name='',thread=None,jdb=None):
    megadl = megacli.mega.Mega({'verbose': True})
    megadl.login()
    try:
        info = megadl.get_public_url_info(megaurl)
        file_name = info['name']
        megadl.download_url(megaurl,dest_path=None,dest_filename=file_name,progressfunc=downloadFile,args=(bot,message,thread))
        if not megadl.stoping:
            processFile(update,bot,message,file_name,thread=thread)
    except:
        files = megaf.get_files_from_folder(megaurl)
        for f in files:
            file_name = f['name']
            megadl._download_file(f['handle'],f['key'],dest_path=None,dest_filename=file_name,is_public=False,progressfunc=downloadFile,args=(bot,message,thread),f_data=f['data'])
            if not megadl.stoping:
                processFile(update,bot,message,file_name,thread=thread)
        pass
    pass

def sendTxt(name,files,update,bot):
    """Envía archivo txt con enlaces"""
    try:
        # Crear el archivo txt
        with open(name, 'w') as txt:
            for i, f in enumerate(files):
                separator = '\n' if i < len(files) - 1 else ''
                txt.write(f['directurl'] + separator)
        
        # Mensaje informativo
        info_msg = f"""<b>📄 Archivo de enlaces generado</b>

📎 <b>Nombre:</b> <code>{name}</code>
🔗 <b>Enlaces incluidos:</b> {len(files)}
⏱️ <b>Duración de enlaces:</b> 8-10 minutos

⬇️ <b>Descarga el archivo TXT abajo</b>"""
        
        bot.sendMessage(update.message.chat.id, info_msg, parse_mode='HTML')
        
        # Enviar el archivo txt
        bot.sendFile(update.message.chat.id, name)
        
        # Limpiar archivo temporal
        os.unlink(name)
        
    except Exception as ex:
        print(f"Error en sendTxt: {str(ex)}")
        # Fallback seguro
        try:
            if os.path.exists(name):
                bot.sendFile(update.message.chat.id, name)
                os.unlink(name)
        except:
            pass

def onmessage(update,bot:ObigramClient):
    try:
        thread = bot.this_thread
        username = update.message.sender.username
        tl_admin_user = os.environ.get('tl_admin_user','Eliel_21')

        jdb = JsonDatabase('database')
        jdb.check_create()
        jdb.load()

        user_info = jdb.get_user(username)

        if username == tl_admin_user or tl_admin_user=='*' or user_info :  # validate user
            if user_info is None:
                if username == tl_admin_user:
                    jdb.create_admin(username)
                else:
                    jdb.create_user(username)
                user_info = jdb.get_user(username)
                jdb.save_data_user(username, user_info)
                jdb.save()
        else:return

        msgText = ''
        try: 
            msgText = update.message.text
        except: 
            msgText = ''

        # ✅ DETECTAR TIPO DE MENSAJE
        is_text = msgText != ''
        
        # ✅ BLOQUEAR SOLO COMANDOS DE CONFIGURACIÓN PARA USUARIOS NORMALES
        isadmin = jdb.is_admin(username)
        
        # Si NO es admin y el mensaje es un COMANDO de configuración, bloquear
        if not isadmin and is_text and any(cmd in msgText for cmd in [
            '/zips', '/account', '/host', '/repoid', '/tokenize', 
            '/cloud', '/uptype', '/proxy', '/dir', '/tutorial', 
            '/myuser', '/files', '/txt_', '/del_', '/delall'
        ]):
            bot.sendMessage(update.message.chat.id,
                           "<b>🚫 Acceso Restringido</b>\n\n"
                           "Los comandos de configuración están disponibles solo para administradores.\n\n"
                           "<b>✅ Puedes usar:</b>\n"
                           "• Enlaces de descarga HTTP/HTTPS\n"
                           "• Comando /start para información",
                           parse_mode='HTML')
            return

        # Si es un mensaje de texto normal (no comando, no enlace)
        if is_text and not msgText.startswith('/') and not 'http' in msgText:
            if isadmin:
                response_msg = """<b>👋 ¡Hola Administrador!</b>

<b>📝 Comandos disponibles:</b>
• /start - Información del bot
• /tutorial - Guía de uso
• /myuser - Mi configuración
• /adduser @user - Agregar usuario
• /banuser @user - Eliminar usuario
• /getdb - Obtener base de datos

<b>🌐 O envía un enlace HTTP/HTTPS para subir archivos</b>"""
            else:
                response_msg = """<b>👋 ¡Bienvenido!</b>

<b>🤖 Bot de Subidas a Moodle</b>

<b>📤 Para usar el bot:</b>
1. Envía cualquier enlace HTTP/HTTPS
2. El bot lo procesará automáticamente
3. Recibirás los enlaces de descarga

<b>🔗 Ejemplo:</b> <code>https://ejemplo.com/archivo.zip</code>

<b>⏱️ Nota:</b> Los enlaces generados duran entre 8-10 minutos

<b>💡 Usa</b> <code>/start</code> <b>para más información</b>"""
            
            bot.sendMessage(update.message.chat.id, response_msg, parse_mode='HTML')
            return

        # comandos de admin (solo para administrador)
        if '/adduser' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                try:
                    user = str(msgText).split(' ')[1]
                    jdb.create_user(user)
                    jdb.save()
                    msg = f'<b>✅ ¡Perfecto!</b> @{user} ahora tiene acceso al bot'
                    bot.sendMessage(update.message.chat.id, msg, parse_mode='HTML')
                except:
                    bot.sendMessage(update.message.chat.id,'<b>❌ Error en el comando:</b> <code>/adduser username</code>', parse_mode='HTML')
            else:
                bot.sendMessage(update.message.chat.id,'<b>❌ No tiene permisos de administrador</b>', parse_mode='HTML')
            return
        if '/banuser' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                try:
                    user = str(msgText).split(' ')[1]
                    if user == username:
                        bot.sendMessage(update.message.chat.id,'<b>❌ No puede banearse a sí mismo</b>', parse_mode='HTML')
                        return
                    jdb.remove(user)
                    jdb.save()
                    msg = f'<b>🚫 Usuario</b> @{user} <b>ha sido baneado</b>'
                    bot.sendMessage(update.message.chat.id, msg, parse_mode='HTML')
                except:
                    bot.sendMessage(update.message.chat.id,'<b>❌ Error en el comando:</b> <code>/banuser username</code>', parse_mode='HTML')
            else:
                bot.sendMessage(update.message.chat.id,'<b>❌ No tiene permisos de administrador</b>', parse_mode='HTML')
            return
        if '/getdb' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                bot.sendMessage(update.message.chat.id,'<b>📦 Base de datos:</b>', parse_mode='HTML')
                bot.sendFile(update.message.chat.id,'database.jdb')
            else:
                bot.sendMessage(update.message.chat.id,'<b>❌ No tiene permisos de administrador</b>', parse_mode='HTML')
            return

        # comandos de usuario (solo para administrador)
        if '/tutorial' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                tuto = open('tuto.txt','r')
                bot.sendMessage(update.message.chat.id,tuto.read())
                tuto.close()
            except:
                bot.sendMessage(update.message.chat.id,'<b>📚 Archivo de tutorial no disponible</b>', parse_mode='HTML')
            return
        if '/myuser' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            getUser = user_info
            if getUser:
                statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
                return
        if '/zips' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            getUser = user_info
            if getUser:
                try:
                   size = int(str(msgText).split(' ')[1])
                   getUser['zips'] = size
                   jdb.save_data_user(username,getUser)
                   jdb.save()
                   msg = f'<b>✅ Zips configurados a</b> {sizeof_fmt(size*1024*1024)} <b>por parte</b>'
                   bot.sendMessage(update.message.chat.id,msg, parse_mode='HTML')
                except:
                   bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/zips tamaño_en_mb</code>', parse_mode='HTML')
                return
        if '/account' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                account = str(msgText).split(' ',2)[1].split(',')
                user = account[0]
                passw = account[1]
                getUser = user_info
                if getUser:
                    getUser['moodle_user'] = user
                    getUser['moodle_password'] = passw
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/account usuario,contraseña</code>', parse_mode='HTML')
            return
        if '/host' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                cmd = str(msgText).split(' ',2)
                host = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['moodle_host'] = host
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/host url_del_moodle</code>', parse_mode='HTML')
            return
        if '/repoid' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                cmd = str(msgText).split(' ',2)
                repoid = int(cmd[1])
                getUser = user_info
                if getUser:
                    getUser['moodle_repo_id'] = repoid
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/repoid id_del_repositorio</code>', parse_mode='HTML')
            return
        if '/tokenize_on' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                getUser = user_info
                if getUser:
                    getUser['tokenize'] = 1
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error activando tokenize</b>', parse_mode='HTML')
            return
        if '/tokenize_off' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                getUser = user_info
                if getUser:
                    getUser['tokenize'] = 0
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error desactivando tokenize</b>', parse_mode='HTML')
            return
        if '/cloud' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                cmd = str(msgText).split(' ',2)
                repoid = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['cloudtype'] = repoid
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/cloud (moodle o cloud)</code>', parse_mode='HTML')
            return
        if '/uptype' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                cmd = str(msgText).split(' ',2)
                type = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['uploadtype'] = type
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/uptype (evidence, draft, blog)</code>', parse_mode='HTML')
            return
        if '/proxy' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                cmd = str(msgText).split(' ',2)
                proxy = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['proxy'] = proxy
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                if user_info:
                    user_info['proxy'] = ''
                    statInfo = infos.createStat(username,user_info,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            return
        if '/dir' in msgText:
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            try:
                cmd = str(msgText).split(' ',2)
                repoid = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['dir'] = repoid + '/'
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo, parse_mode='HTML')
            except:
                bot.sendMessage(update.message.chat.id,'<b>❌ Error:</b> <code>/dir nombre_carpeta</code>', parse_mode='HTML')
            return
        if '/cancel_' in msgText:
            try:
                cmd = str(msgText).split('_',2)
                tid = cmd[1]
                tcancel = bot.threads[tid]
                msg = tcancel.getStore('msg')
                tcancel.store('stop',True)
                time.sleep(3)
                bot.editMessageText(msg,'<b>❌ Tarea Cancelada</b>', parse_mode='HTML')
            except Exception as ex:
                print(str(ex))
            return

        message = bot.sendMessage(update.message.chat.id,'<b>⏳ Procesando...</b>', parse_mode='HTML')

        thread.store('msg',message)

        if '/start' in msgText:
            welcome_text = """<b>🤖 Bot de Subidas a Moodle</b>

Sube archivos directamente a Moodle desde enlaces web.

<b>👨‍💻 Desarrollado por:</b> @Eliel_21

<b>⏱️ Nota:</b> Los enlaces generados duran entre 8-10 minutos

<b>🚀 Envía cualquier enlace HTTP/HTTPS para comenzar</b>"""
            
            bot.editMessageText(message, welcome_text, parse_mode='HTML')
        elif '/files' == msgText and user_info['cloudtype']=='moodle':
             if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
             proxy = ProxyCloud.parse(user_info['proxy'])
             client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],proxy=proxy)
             loged = client.login()
             if loged:
                 files = client.getEvidences()
                 filesInfo = infos.createFilesMsg(files)
                 bot.editMessageText(message,filesInfo, parse_mode='HTML')
                 client.logout()
             else:
                bot.editMessageText(message,'<b>❌ Error de conexión</b>\n• Verifique su cuenta\n• Servidor: '+client.path, parse_mode='HTML')
        elif '/txt_' in msgText and user_info['cloudtype']=='moodle':
             if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
             findex = str(msgText).split('_')[1]
             findex = int(findex)
             proxy = ProxyCloud.parse(user_info['proxy'])
             client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],proxy=proxy)
             loged = client.login()
             if loged:
                 evidences = client.getEvidences()
                 evindex = evidences[findex]
                 txtname = evindex['name']+'.txt'
                 sendTxt(txtname,evindex['files'],update,bot)
                 client.logout()
                 bot.editMessageText(message,'<b>📄 Archivo TXT generado:</b>', parse_mode='HTML')
             else:
                bot.editMessageText(message,'<b>❌ Error de conexión</b>\n• Verifique su cuenta\n• Servidor: '+client.path, parse_mode='HTML')
             pass
        elif '/del_' in msgText and user_info['cloudtype']=='moodle':
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            findex = int(str(msgText).split('_')[1])
            proxy = ProxyCloud.parse(user_info['proxy'])
            client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],
                                   proxy=proxy)
            loged = client.login()
            if loged:
                evfile = client.getEvidences()[findex]
                client.deleteEvidence(evfile)
                client.logout()
                bot.editMessageText(message,'<b>🗑️ Archivo eliminado</b>', parse_mode='HTML')
            else:
                bot.editMessageText(message,'<b>❌ Error de conexión</b>\n• Verifique su cuenta\n• Servidor: '+client.path, parse_mode='HTML')
        elif '/delall' in msgText and user_info['cloudtype']=='moodle':
            if not isadmin:
                bot.sendMessage(update.message.chat.id,'<b>❌ Comando restringido a administradores</b>', parse_mode='HTML')
                return
            proxy = ProxyCloud.parse(user_info['proxy'])
            client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],
                                   proxy=proxy)
            loged = client.login()
            if loged:
                evfiles = client.getEvidences()
                for item in evfiles:
                	client.deleteEvidence(item)
                client.logout()
                bot.editMessageText(message,'<b>🗑️ Todos los archivos eliminados</b>', parse_mode='HTML')
            else:
                bot.editMessageText(message,'<b>❌ Error de conexión</b>\n• Verifique su cuenta\n• Servidor: '+client.path, parse_mode='HTML')       
        elif 'http' in msgText:
            url = msgText
            ddl(update,bot,message,url,file_name='',thread=thread,jdb=jdb)
        else:
            bot.editMessageText(message,'<b>❌ No se pudo procesar el mensaje</b>', parse_mode='HTML')
    except Exception as ex:
           print(str(ex))

def start_health_server(port):
    """Inicia un servidor HTTP simple para health checks"""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(5)
        print(f"✅ Health check server running on port {port}")
        
        while True:
            try:
                client_socket, addr = server_socket.accept()
                request = client_socket.recv(1024).decode('utf-8')
                
                # Responder con HTTP 200 OK
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nBot is running!"
                client_socket.send(response.encode('utf-8'))
                client_socket.close()
            except Exception as e:
                print(f"Health check error: {e}")
                break
                
    except Exception as e:
        print(f"❌ Health server failed: {e}")

def main():
    bot_token = os.environ.get('bot_token')

    #decomentar abajo y modificar solo si se va a poner el token del bot manual
    #bot_token = 'BOT TOKEN'

    bot = ObigramClient(bot_token)
    bot.onMessage(onmessage)
    
    # Obtener puerto de Render
    port = int(os.environ.get("PORT", 5000))
    
    # Iniciar servidor de health check en un hilo separado
    health_thread = threading.Thread(target=start_health_server, args=(port,))
    health_thread.daemon = True
    health_thread.start()
    
    print(f"🚀 Bot starting with health check on port {port}")
    
    # Ejecutar el bot
    bot.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        # Reintentar después de 5 segundos
        time.sleep(5)
        main()
