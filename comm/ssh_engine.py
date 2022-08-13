'''Copy Left: qinhuawei@outlook.com 2016-2022
Microsoft Visual C++ Compiler for Python 2.7
    http://www.microsoft.com/en-us/download/details.aspx?id=44266
C:\tools\Python27\Scripts\pip.exe install paramiko
On Linux,  apt-get install build-essential libssl-dev libffi-dev python-dev
apt-get install python-paramiko'''
import logging,re,time,socket,os,datetime,paramiko,threading

def set_prompt(self, prompt):
    self.prompt = re.escape(prompt)  # r'[\r\n]+%s' %re.escape(prompt)  not always OK, as <cat a file>
    #logging.debug('chan %s prompt = %s' %(self.get_name(), prompt))

def wait_expect(self,timeout=0, expect_raw=None, expect_re=None,log_on_screen=True):
    exec_buff = ''

    ts_start = time.time()
    if timeout:
        if expect_raw:
            expect_re = re.escape(expect_raw)
        if not expect_re:
            expect_re = self.prompt
        while time.time() - ts_start <= timeout:
            try:
                piece_buff =  self.recv(65535).decode('utf-8')
                exec_buff = '%s%s' %(exec_buff,piece_buff)
                if log_on_screen:
                    print(piece_buff, end='')
                self.log_file.write(piece_buff)
                if re.search(expect_re, exec_buff, re.S|re.DOTALL):
                    self.log_file.write('\n== %s wait_match OK\n' %self.get_name())
                    logging.debug        ('== %s wait_match OK' %self.get_name())
                    return exec_buff
            except socket.timeout:
                pass
    else:
        while time.time() - ts_start <= 1 and not self.recv_ready:
            print('.', end='')
            time.sleep(0.05)
        return self.exec_command(chr(3), match_command=False)

    logging.info          ('== %s wait_match TIMEOUT %.1f' %(self.get_name(),timeout))
    self.log_file.write ('\n== %s wait_match TIMEOUT %.1f\n' %(self.get_name(),timeout))
    raise Exception('WAIT_MATCH', exec_buff)

def exec_command(self, command, timeout=9, prompt=None, expect_raw=None, expect_re=None, auto_yes=False, match_command=True, with_password=None, is_bash=True):
    if not command:
        logging.error('command should NOT be empty. Refresh buffer please use refresh_buffer')
        return
    command = command.strip()
    self.log_file.write('\n==%s command Start %s...\n' %(datetime.datetime.now().strftime("%H:%M:%S.%f"),command[:8]))
    self.refresh_buffer(recv_anyway=True)
    self.send('%s\n' %command)

    if prompt:
        self.set_prompt(prompt)

    shell_expect    = None
    cmd_piece       = command

    if not expect_re:
        if expect_raw:
            expect_re = re.escape(expect_raw)

        if not expect_re:
            expect_re = self.prompt

        if match_command:
            matches = re.search(r'[\r\n]+([^\r\n]+)$',command)
            if matches:
                # too long command string possibly causes input/output mismatch.
                cmd_piece = matches.group(1)

            if not is_bash:
                shell_expect = expect_re

            expect_re = r'%s..*%s' %(re.escape(cmd_piece[:30]), expect_re)  # there is possible the command string being splited.

    if self.log_on_screen:
        logging.debug('==%s.%s [%s], timeout [%.1f], expect_re [%s], prompt [%s], expect_raw [%s]' %(self.hostname, self.get_name(), command, timeout, expect_re, self.prompt, expect_raw, ))

    exec_buff = ''
    ts_start = time.time()
    while time.time() - ts_start <= timeout:
        try:
            piece_buff =  self.recv(65535).decode('utf-8')
            if not piece_buff:
                continue
            exec_buff = '%s%s' %(exec_buff,piece_buff)
            if self.log_on_screen:
                print(piece_buff, end='') #print piece_buff,
            self.log_file.write(piece_buff)

            if re.search(expect_re, exec_buff, re.S|re.DOTALL):
                self.log_file.write('\n==%s %s command OK\n' %(datetime.datetime.now().strftime("%H:%M:%S.%f"),self.get_name()))
                if self.log_on_screen:
                    logging.debug        ('==%s.%s [%s] OK' %(self.hostname, self.get_name(), cmd_piece[:60]))
                return exec_buff
            if shell_expect:
                for iii in range(0,len(cmd_piece)-6):
                    tmp_pattern = r'%s.*%s' %(re.escape(cmd_piece[iii:iii+6]), shell_expect)
                    if re.search(tmp_pattern, exec_buff, re.S|re.DOTALL):
                        self.log_file.write('\n== %s command pattern [%s] OK\n' %(self.get_name(),tmp_pattern))
                        logging.debug        ('== %s.%s [%s] OK' %(self.hostname, self.get_name(), cmd_piece[:60]))
                        return exec_buff
            if auto_yes:
                if re.search(r'\Wyes\W', exec_buff, re.S|re.I):
                    self.send('yes\n')
                    auto_yes = False
                    continue
                if re.search(r'y\/n', exec_buff, re.S|re.I):
                    self.send('y\n')
                    auto_yes = False
                    continue
                if re.search(r'\[y\/d\/N\]', exec_buff, re.S|re.I):
                    self.send('y\n')
                    auto_yes = False
                    continue
                if exec_buff.count('[y]es'):
                    self.send('y\n')
                    auto_yes = False
                    continue
            if with_password:
                if re.search(r'\spassword:|Password', exec_buff, re.S|re.I):
                    self.send('%s\n' %with_password)
                    with_password = None
                    continue
        except socket.timeout:
            #print '.',
            pass

    logging.info          ('== %s.%s command TIMEOUT %.1f [%s]' %(self.hostname,self.get_name(),timeout,command))
    self.log_file.write ('\n==%s %s command TIMEOUT %.1f [%s]\n' %(datetime.datetime.now().strftime("%H:%M:%S.%f"),self.get_name(),timeout,command))
    raise Exception('CMD_TIMEOUT', exec_buff)

def guess_prompt(self,):
    time.sleep(0.2)
    self.refresh_buffer(recv_anyway=True)
    self.send('true\n')
    recv_buff = ''
    prompt = ''
    for iii in range(2019):
        time.sleep(0.2)
        recv_buff = '%s%s' %(recv_buff, self.refresh_buffer(recv_anyway=True))
        if recv_buff.count('You have new mail') or len(recv_buff)>60:
            self.send('true\n')
            recv_buff = ''
            continue
        if recv_buff.count('true'):
            matches = re.search(r'true[\r\n]+([^\r\n\s]+)', recv_buff, re.S)
            if matches:
                prompt = matches.group(1)
                break
        if iii > 20:
            raise Exception('guess_prompt', recv_buff)
    logging.warning('== %s.%s guess_prompt [%s]' %(self.hostname,self.get_name(), prompt))
    self.exec_command('true', prompt=prompt, timeout=20)
    return prompt

def refresh_buffer(self, recv_anyway=False):
    try:
        # while not tunnel.closed or tunnel.recv_ready() or tunnel.recv_stderr_ready():
        if self.recv_ready() or recv_anyway:
            piece_buff =  self.recv(65535).decode('utf-8')
            if self.log_on_screen:
                print(piece_buff, end='') #print piece_buff,
            self.log_file.write(piece_buff)
            return piece_buff
    except:
        return ''

# On windows, winpty python uas.py -r demo.neo -e ssh -o testbed
def posix_shell(self,):
    #https://github.com/paramiko/paramiko/blob/master/demos/interactive.py
    if os.name == 'nt':
        import threading,sys
        import msvcrt
        sys.stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")
        self.send('date\n')
        self.settimeout(0.001)
        def writeall():
            while True:
                raw_data = None
                try:
                    raw_data = self.recv(65535)
                    data = raw_data.decode('utf-8')
                    if data:
                        sys.stdout.write(data)
                        sys.stdout.flush()
                except socket.timeout:
                    pass
                except UnicodeDecodeError:
                    #print('UnicodeDecodeError')
                    if raw_data:
                        sys.stdout.write(data)
                        sys.stdout.flush()

        writer = threading.Thread(target=writeall, args=())
        writer.setDaemon(True)
        writer.start()

        try:
            while True:
                d = msvcrt.getch()
                if not d:
                    continue
                # functional key is \xe0 or \x00 followed other key.
                if d == b'\xe0' or d == b'\x00':
                    msvcrt.getch()
                    d = sys.stdin.readline()
                self.send(d)
        except:
            pass
    else:
        from paramiko.py3compat import u
        import tty,termios,select,sys
        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            self.settimeout(0.0)
    
            while True:
                r, w, e = select.select([self, sys.stdin], [], [])
                for rrr in r:
                    if self == rrr:
                        try:
                            x = u(self.recv(65535).decode('utf-8'))
                            if len(x) == 0:
                                sys.stdout.write('\r\n*** EOF\r\n')
                                break
                            sys.stdout.write(x)
                            sys.stdout.flush()
                        except socket.timeout:
                            pass
                    if sys.stdin == rrr:
                        x = sys.stdin.read(1)
                        if len(x) == 0:
                            break
                        self.send(x)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

paramiko.channel.Channel.guess_prompt   = guess_prompt
paramiko.channel.Channel.set_prompt     = set_prompt
paramiko.channel.Channel.__exec_command = paramiko.channel.Channel.exec_command
# overwrite exec_command becuase calling original exec_command on interactive channel causes abnormal [Channel closed.]
paramiko.channel.Channel.exec_command   = exec_command
paramiko.channel.Channel.refresh_buffer = refresh_buffer
paramiko.channel.Channel.posix_shell    = posix_shell
paramiko.channel.Channel.wait_expect    = wait_expect

class ssh_connect():
    def __init__(self, hostname, username, passwd=None, port=22, key_filename=None, alias=None, log_folder='.', proxy_list=None):
        if alias:
            self.hostname = alias
        else:
            self.hostname = hostname
        self.log_folder = log_folder
        self._sftp    = None
        self.chan_dict = {}

        if proxy_list:
            # How to SSH to server through a jumping server.
            # https://stackoverflow.com/questions/35304525/nested-ssh-using-python-paramiko
            active_jumper = None
            jump_chan  = None
            j_transport = None
            for jumper in proxy_list:
                if not active_jumper:
                    j_transport = paramiko.Transport((jumper['host'], jumper['port']))
                    j_transport.connect(username=jumper['user'], password=jumper['passwd'])
                else:
                    jump_chan = j_transport.open_channel("direct-tcpip", (jumper['host'],jumper['port']), (active_jumper['host'],active_jumper['port']),timeout=5) 
                    j_client=paramiko.SSHClient()
                    j_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    j_client.connect(jumper['host'], port=jumper['port'], username=jumper['user'], password=jumper['passwd'], sock=jump_chan)
                    j_transport = j_client.get_transport()
                active_jumper = jumper

            jump_chan = j_transport.open_channel("direct-tcpip", (hostname, port), (active_jumper['host'],active_jumper['port']),timeout=5)

            jhost=paramiko.SSHClient()
            jhost.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            jhost.connect(hostname, port=port, username=username, password=passwd, sock=jump_chan)
            self._transport = jhost.get_transport()
            self.j_transport = j_transport
        else:
            self._transport = paramiko.Transport((hostname, port))
            try:
                self._transport.connect(username=username, password=passwd)
            except:
                private_key = paramiko.RSAKey.from_private_key_file(key_filename)
                self._transport.connect(username=username, pkey=private_key)
        self._transport.use_compression(True)
        self._transport.set_keepalive(60)
        logging.info('========= login %s@%s OK ========' %(username,hostname))

    def close(self):
        chan_name_list = list(self.chan_dict.keys())
        for chan_name in chan_name_list:
            self.chan_dict[chan_name].log_on_screen = False
            self.close_shell(chan_name)
        self._transport.close()
        try:
            self.j_transport.close()
        except:
            pass
        try:
            self._sftp.close()
        except:
            pass
        logging.debug('=== connection closed [%s] ===' %self.hostname)

    def upload_folder(self, local_folder, remote_root, file_wildcard=None):
        if not os.path.isdir(local_folder):
            raise Exception('BAD_PATH', local_folder)
        if remote_root[-1] == '/' or remote_root[-1] == '\\':
            remote_root = remote_root[:-1]
        if local_folder[-1] == '/' or local_folder[-1] == '\\':
            local_folder = local_folder[:-1]
        for r, d, f in os.walk(local_folder):
            for file in f:
                local_file = os.path.join(r, file)
                logging.debug(local_file)
                if os.path.isfile(local_file):
                    if file_wildcard and 0 == file.count(file_wildcard):
                        continue
                    rel_path = os.path.relpath(os.path.dirname(local_file), os.path.dirname(local_folder))
                    remote_path = '%s/%s' %(remote_root, rel_path)
                    remote_path = remote_path.replace('\\', '/')
                    self.upload(local_file, remote_path)

    def download_folder(self, remote_path, local_path, del_files=False, file_wildcard=None): # file_wildcard work as string.count
        file_count = 0
        if remote_path[-1] == '/' or remote_path[-1] == '\\':
            remote_path = remote_path[:-1]
        if local_path[-1] == '/' or local_path[-1] == '\\':
            local_path = local_path[:-1]

        if os.path.exists(local_path) and os.path.isdir(local_path):
            local_path = os.path.join(local_path, os.path.basename(remote_path))

        if not self._sftp:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)

        from stat import S_ISREG, S_ISDIR
        fileattr = self._sftp.lstat(remote_path)
        if S_ISREG(fileattr.st_mode):
            try:
                logging.info('src [%s], local [%s]' % (remote_path, local_path))
                return self._sftp.get(remote_path, local_path)
            except:
                pass

        def sftp_walk(sftp,remotepath):
            path=remotepath
            files=[]
            folders=[]
            for f in sftp.listdir_attr(remotepath):
                if S_ISDIR(f.st_mode):
                    folders.append(f.filename)
                else:
                    files.append(f.filename)
            if files:
                yield path, files
            for folder in folders:
                #new_path=os.path.join(remotepath,folder)
                new_path = '%s/%s' %(remotepath,folder)
                for x in sftp_walk(sftp,new_path):
                    yield x

        for path,files  in sftp_walk(self._sftp, remote_path):
            for file in files:
                if file_wildcard and 0 == file.count(file_wildcard):
                    continue
                source_file = '%s/%s' %(path,file)
                local_folder = local_path
                if remote_path < path:
                    local_folder = os.path.join(local_path, path[1+len(remote_path):])
                    #logging.critical('local_path [%s], local_folder [%s]' %(local_path, local_folder))
                if os.path.exists(local_folder):
                    if not os.path.isdir(local_folder):
                        raise Exception('NOT_A_FOLDER', local_folder)
                else:
                    os.makedirs(local_folder)

                local_file = os.path.join(local_folder,file)
                logging.info('src [%s], local [%s]' %(source_file,local_file))
                self._sftp.get(source_file, local_file)
                file_count = file_count + 1
                if del_files:
                    self.remove_file(source_file)
        return file_count

    def get_files(self, file_list, local_root, remote_root):
        files = re.split('[\r\n]+', file_list)
        for file in files:
            if re.search(r'\w', file):
                remote_file = '%s/%s' % (remote_root, file)
                local_file = os.path.join(local_root, file)
                local_path = os.path.dirname(local_file)
                logging.info(remote_file)
                logging.info(local_file)
                self.download(remote_file, local_path)

    def put_files(self, file_list, local_root, remote_root):
        files = re.split('[\r\n]+', file_list)
        for file in files:
            local_file = os.path.join(local_root, file)
            if os.path.isfile(local_file):
                remote_path = '%s/%s' % (remote_root, os.path.dirname(file))
                logging.info(local_file)
                logging.info(remote_path)
                self.upload(local_file, remote_path)

    def remove_file(self, remote_file):
        if not self._sftp:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        self._sftp.remove(remote_file)

    def download(self, remote_file, local_path=None):
        if not self._sftp:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        if local_path:
            local_file =  '%s/%s' %(local_path,os.path.basename(remote_file))
            if not os.path.isdir(local_path):
                os.makedirs(local_path)
        else:
            local_file = os.path.basename(remote_file)            
        logging.info          ('========= %s sftp dl [%s], local [%s]' %(self.hostname,remote_file,local_file))
        self._sftp.get(remote_file, local_file)
        logging.info          ('========= %s sftp OK [%s], local [%s]' %(self.hostname,remote_file,local_file))

    def mkdir_p(self, remote_directory):
        if not self._sftp:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        if remote_directory == '/' or remote_directory == '':
            return
        try:
            self._sftp.chdir(remote_directory) # sub-directory exists
        except IOError:
            dirname, basename = os.path.split(remote_directory.rstrip('/'))
            self.mkdir_p(dirname) # make parent directories
            self._sftp.mkdir(remote_directory) # sub-directory missing, so created it

    def upload(self, local_file, remote_path=None, remote_file=None):
        if not self._sftp:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)

        if not remote_file:
            remote_file = '%s/%s' %(remote_path,os.path.basename(local_file))

        if not remote_path:
            remote_file = remote_file.replace('/', '\\')
            remote_path = os.path.dirname(remote_file)

        remote_path = remote_path.replace('\\', '/')
        remote_file = remote_file.replace('\\', '/')
        self.mkdir_p(remote_path)

        if os.name == 'nt':
            local_file = local_file.replace('/', '\\')

        logging.info          ('========= %s sftp up [%s], remote[%s]' %(self.hostname,local_file,remote_file))

        self._sftp.put(local_file, remote_file)
        logging.info          ('========= %s sftp OK [%s], remote[%s]' %(self.hostname,local_file,remote_file))

    def close_shell(self, chan_name):
        channel = self.chan_dict.pop(chan_name)
        delattr(self, chan_name)
        channel.send('\n')
        channel.send(chr(4))
        channel.refresh_buffer(recv_anyway=True)

        channel.log_file.write('\n==%s shell closed [%s] [%s] =========\n' %(datetime.datetime.now().strftime("%H:%M:%S.%f"),self.hostname,chan_name))
        channel.log_file.close()
        channel.close()
        logging.debug('=== shell closed [%s] [%s] ===' %(self.hostname,chan_name))

    def invoke_shell(self, chan_name, prompt='#', log_on_screen=True, close_and_open=False):
        try:
            if close_and_open:
                self.close_shell(chan_name)
                logging.warning('%s chan [%s] close_and_open=True' %(self.hostname, chan_name))
        except:
            pass

        channel = self._transport.open_session()
        setattr(self, chan_name, channel)  # possible failed at chan_name no a proper variable name.

        channel.get_pty()
        channel.invoke_shell()
        channel.settimeout(3)
        channel.log_on_screen = log_on_screen
        channel.log_file = open('%s/%s_%s.log' %(self.log_folder,self.hostname,chan_name), 'a', 1)

        try:
            piece_buff =  channel.recv(65535).decode('utf-8')
            if channel.log_on_screen:
                print(piece_buff, end='') #print piece_buff,
            channel.log_file.write(piece_buff)
        except socket.timeout:
            pass

        channel.settimeout(0.001)
        channel.log_file.write('\n========= invoke_shell %s conn %s OK =========\n' %(self.hostname,chan_name))
        channel.set_name(chan_name)
        channel.resize_pty(width=65535, height=65535)
        channel.hostname = self.hostname
        channel.set_prompt(prompt)
        self.chan_dict[chan_name] = channel
        logging.debug('=== invoke_shell %s conn %s OK ===' %(self.hostname, chan_name))
        return channel

import traceback
def go_thread(function, args=(), kwargs={}, wait_finish=True):
    try:
        go_thread.t_list
    except:
        go_thread.t_dict = {}
        go_thread.t_list = []

    def join_threads(timeout=9):
        if not hasattr(go_thread, 't_list'):
            return
        for tmp_thr in go_thread.t_list:
            for iii in range(timeout):
                tmp_thr.join(timeout=1)
        go_thread.list = []
        for _, err_info in go_thread.t_dict.items():
            logging.critical(err_info)
        if go_thread.t_dict:
            raise Exception('go_thread')

    go_thread.join_threads = join_threads

    # use wrapper to try catch
    def wrapper():
        try:
            function(*args,**kwargs)
        except Exception as e:
            logging.exception('GO_THREAD: {}({},{}) ~~~~~~'.format(function.__name__ ,args,kwargs))
            tid = threading.get_ident()
            go_thread.t_dict[tid] = 'GO_THREAD: {}({},{})\n{}'.format(function.__name__ ,args,kwargs, e)

    tmp_thr = threading.Thread(target=wrapper, args=())
    tmp_thr.setDaemon(True)
    tmp_thr.start()
    if wait_finish:
        go_thread.t_list.append(tmp_thr)
    # go_thread(connection.channel.exec_command, args=('top -b',), kwargs={'timeout':3600,'expect_raw':'keep UAS waithe re, to collect log.'})

if __name__ == "__main__":
    import sys
    connection =  ssh_connect('192.168.56.254', 'root', passwd='pdg.net')
    connection.invoke_shell('linux')

    connection.linux.exec_command('date;ping 127.0.0.1 -c2;date')
    print (connection.linux.getpeername())

    print ('---------- now explain why exec_command been overwritten ------------')
    # on interactive channel calling __exec_command would cause the channel immediately shutdown.
    # then open a new channel
    import select
    channel = connection._transport.open_session()
    def __exec_command(command, timeout=5):
        channel.__exec_command(command)
        for iii in range(timeout*10):
            try:
                rl, wl, xl = select.select([channel],[],[],0.1)
                if len(rl) > 0:
                    print(channel.recv(65535))
            except KeyboardInterrupt:
                print("Ctrl+C")
                break

    __exec_command("date;ping 127.0.0.1 -c2;date")

    try:
        __exec_command("export test_if_env_exist=test_if_env_exist")
    except Exception as e:
        print ('---------- the channel closed just after one command executed. ------------')
        print(e)
        channel = connection._transport.open_session()
        __exec_command('''export test_if_env_exist=test_if_env_exist;echo "test [$test_if_env_exist"]''')
    channel = connection._transport.open_session()
    __exec_command('''echo "test [$test_if_env_exist"]''')
    # no value in $test_if_env_exist after channel re-open. This is why exec_command overwritten.

    import os
    go_thread(os.system, args='ping 8.8.8.8 -n 4')
    go_thread(os.system, args='ping 127.0.0.1 -n 3')
    go_thread(os.system, args='ping 163.com -n 2')
    go_thread.join_threads()