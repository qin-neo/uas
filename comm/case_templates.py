# qinhuawei@outlook.com
import logging,sys,threading,os,time,re,socket
from comm.ssh_connections import manage_connections, create_connections
from comm.ssh_engine import go_thread

class case_template_00(manage_connections):
    conn_dict = {}
    required_connections = {}

    def __init__(self, conn_cfg, case_parameters, log_folder, log_on_screen):
        self.conn_cfg = conn_cfg
        self.log_folder = log_folder
        self.parameters = case_parameters
        self.log_on_screen = log_on_screen
        self.case_result = None

    def run(self):
        self.create_connections()
        logging.critical('=========UAS prepare =========')
        self.case_prepare()
        logging.critical('=========UAS steps ===========')
        self.case_steps()
        logging.critical('=========UAS steps OK ========')

    def end(self):
        self.close_all_connections()

    def case_cleanup(self):
        pass

    def press_y_2_continue(self):
        choice = ''
        while choice != 'y':
            choice=input('Ready to continue? (y/n):').lower()

    def get_disk_colon(self):
        return os.path.abspath(__file__)[:2]

    def zip_folder(self, target_folder, zip_path_file):
        list_7z = [r'C:/Program Files/7-Zip/7z.exe', r'D:\tools\7-Zip\7z.exe']
        for win_7z in list_7z:
            if os.path.isfile(win_7z):
                system_cmd = 'del %s & "%s" a -tZip %s %s' % (zip_path_file, win_7z, zip_path_file, target_folder)
                logging.info(system_cmd)
                if 0 != os.system(system_cmd):
                    raise Exception(zip_path_file, system_cmd)
                return
        raise Exception('NO_7Z_EXE', system_cmd)

    def uas(self, conn_name):
        # python -m http.server 8000
        try:
            target_folder = self.conn_dict[conn_name].config['uas_root']
        except:
            target_folder = '/opt'

        connection = self.create_conn(conn_name)
        channel = self.create_conn_chan(conn_name, 'linux', close_and_open=True)

        zip_file = 'uas.tar.bz2'

        if os.name == 'nt':
            tmp_file = 'uas.tar'
            win_7z = r'C:/Program Files/7-Zip/7z.exe'
            os.system('rmdir/S/Q log; del results.log;')
            uas_folder = os.path.basename(os.path.dirname(os.path.realpath(sys.modules['__main__'].__file__)))
            logging.info(uas_folder)
            os.system('cd .. & del %s & "%s" a -ttar %s %s & "%s" a -tgzip %s %s & del %s' %(zip_file,win_7z,tmp_file, uas_folder,win_7z,zip_file,tmp_file,tmp_file))
        else:
            uas_path = os.path.dirname(os.path.realpath(sys.argv[0]))
            os.system('cd %s;rm -rf log results.log;cd ..;rm uas.tar.bz2;tar -cjf %s uas/;' %(uas_path,zip_file))

        connection.upload('../%s' %zip_file, target_folder)
        channel.exec_command('''sh -c 'cd %s; rm uas -rf; mkdir -p %s/uas;tar -xf %s -C %s/uas --strip-components=1; cd %s/uas; rm log -rf; rm results.log -f;pyclean .';''' %(target_folder,target_folder,zip_file,target_folder,target_folder), timeout=20)

        recv_buff = channel.exec_command('cat ~/.bashrc')
        if not recv_buff.count('alias uu='):
            channel.exec_command('''echo "alias uu='cd %s/uas/;python uas.py -r '" >> ~/.bashrc''' %(target_folder))

    def ssh(self, conn_name,):
        self.create_conn(conn_name)
        channel = self.create_conn_chan(conn_name, 'linux')
        channel.posix_shell()

    def dl(self, conn_name, remote_folder, local_folder, file_wildcard=None):
        self.create_conn(conn_name)
        conn = self.conn_dict[conn_name]
        conn.download_folder(remote_folder, local_folder, file_wildcard=file_wildcard)

    def ul(self, conn_name, local_folder, remote_folder, file_wildcard=None):
        self.create_conn(conn_name)
        conn = self.conn_dict[conn_name]
        if os.path.isfile(local_folder):
            return conn.upload(local_folder, remote_folder)

        conn.upload_folder(local_folder, remote_folder, file_wildcard=file_wildcard)

    def ping_test(self, channel, target_ip, source_ip='', retry_times=3):
        if source_ip:
            source_ip = '-I %s' %(source_ip)
        for iii in range(retry_times):
            recv_buff = channel.exec_command('ping %s -c3 -i0.1 -W1 %s' % (target_ip, source_ip))
            if recv_buff.count(', 0% packet loss'):
                return
        raise Exception('PING', recv_buff)

    def web_check(self, channel, url):
        recv_buff = ''
        for iii in range(5):
            try:
                recv_buff = channel.exec_command(url, timeout=3)
                if recv_buff.count('Failed') or recv_buff.count('404'):
                    raise Exception('WEB', recv_buff)
                return
            except:
                logging.exception('---- web_check %s -----' %(channel.hostname))
                time.sleep(1)
        raise Exception(channel.hostname, recv_buff)

    def create_ssh_by_list(self, conn_list):
        def create_linux(conn_name):
            self.create_conn(conn_name)
            self.create_conn_chan(conn_name, 'linux')

        for conn_name in conn_list:
            go_thread(create_linux, args=(conn_name,), kwargs={})
        go_thread.join_threads(60)

    def threading_channel(self, chan, command, timeout=2592000):
        try:
            if chan.thread_handler.isAlive():
                logging.critical('%s is occupied.' %(chan.set_name()))
                raise Exception('go_thread_channel', '%s is occupied.' %(chan.set_name()))
        except AttributeError:
            pass

        def wrapper():
            try:
                chan.threading_buff = chan.exec_command(command, timeout=timeout)
            except:
                logging.exception(f'====== threading_channel {chan.get_name()} [{command}] timeout={timeout} ======')

        chan.thread_handler = threading.Thread(target=wrapper, args=())
        chan.thread_handler.setDaemon(True)
        chan.thread_handler.start()

    def threading_channel_join(self, timeout=9):
        for conn_name, conn in self.conn_dict.items():
            for chan_name, chan in conn.chan_dict.items():
                try:
                    if chan.thread_handler.isAlive():
                        chan.thread_handler.join(timeout=timeout)
                except AttributeError:
                    pass

    def threading_channel_end(self):
        for conn_name, conn in self.conn_dict.items():
            for chan_name, chan in conn.chan_dict.items():
                try:
                    #logging.info(f'{conn_name} {chan_name}')
                    chan.send(chr(3))
                except: #AttributeError:
                    pass

    def throughput_translate(self, throughput):
        if throughput.endswith('M'):
            return throughput[:-1]
        elif throughput.endswith('K'):
            return float(throughput[:-1]) / 1024
        elif throughput.endswith('G'):
            return float(throughput[:-1]) * 1024
        else:
            return 0

    def kvm(self, conn_name):
        self.create_conn(conn_name)
        channel = self.create_conn_chan(conn_name, 'linux')
        channel.exec_command('yum install -y --nogpgcheck libvirt qemu-kvm virt-install libvirt-daemon*', timeout=600)
        channel.exec_command('systemctl start libvirtd.service', timeout=60)
        recv_buff = channel.exec_command('service libvirtd status', )
        if not recv_buff.count('running'):
            raise Exception('libvirtd', recv_buff)

        # qcows access permission denied:
        # vi /etc/libvirt/qemu.conf
        # user = "root"
        # group = "root"
        # service libvirtd restart
        # error: Cannot access storage file
        channel.exec_command('''
sed -i 's/#user = "root"/user = "root"/' /etc/libvirt/qemu.conf
sed -i 's/#group = "root"/group = "root"/' /etc/libvirt/qemu.conf
''')
        channel.exec_command('systemctl enable libvirtd;systemctl restart libvirtd')

        recv_buff = channel.exec_command('virsh list')
        if recv_buff.count(' Id    Name                           State'):
            return
        if recv_buff.count('error: failed to connect to the hypervisor'):
            channel.exec_command('ssystemctl start libvirtd.service')
        recv_buff = channel.exec_command('virsh list')
        if recv_buff.count(' Id    Name                           State'):
            return
        raise Exception('virsh', recv_buff)

        recv_buff = channel.exec_command('lsmod | grep kvm --color=never')
        if not recv_buff.count('kvm_intel'):
            raise Exception('KVM_Module', recv_buff)

    def date(self, host_list=None):
        if not host_list:
            host_list = self.host_list
        else:
            if host_list.__class__ == str:
                host_list = [host_list,]

        for conn_name in host_list:
            self.create_conn(conn_name)
            self.create_conn_chan(conn_name, 'linux')

        ts_now = time.strftime("%d %b %Y %H:%M:%S")
        for conn_name in host_list:
            channel = self.conn_dict[conn_name].linux
            go_thread(channel.exec_command, args=(f'date -s "{ts_now}";sed -i "s/#MaxSessions 10/MaxSessions 100/" /etc/ssh/sshd_config; service sshd restart',), kwargs={'timeout': 9})
        go_thread.join_threads()

    def vcpupin(self, vm_name):
        vm_dict = self.vm_cfg_dict[vm_name]
        conn_name = vm_dict['conn_name']
        connection = self.create_conn(conn_name)
        channel = self.create_conn_chan(conn_name, 'linux')

        host_cpu_list = vm_dict['vcpupin']
        if vm_dict['vcpus'] != len(host_cpu_list):
            raise Exception('vcpupin', '%s CPU numbers not match!' %(vm_name))
        for iii in range(vm_dict['vcpus']):
            # virsh vcpupin ipvs1 0 1
            channel.exec_command('virsh vcpupin %s %d %d' %(vm_name, iii, host_cpu_list[iii]))

    def create_ns_chan(self, ns_name, conn_name, chan_name=''):
        if not chan_name:
            chan_name = f'linux_{ns_name}'
        self.create_conn(conn_name)
        chan = self.create_conn_chan(conn_name, chan_name, close_and_open=True)
        recv_buff = chan.exec_command(f'ip netns exec {ns_name} bash')
        if recv_buff.count('Cannot open network namespace'):
            raise Exception(ns_name, recv_buff)
        return chan

    # lldptool -n -t -i ens3f0
    def vf(self, pf_name, host_list=None, host_name=None, vf_num=4):
        # pf_name = 'enp59s0f1'
        if not host_list:
            if not host_name:
                raise Exception('host_list or host_name')
            host_list = [host_name, ]

        grub2_cfg = '/boot/efi/EFI/centos/grub.cfg'
        for host_name in host_list:
            reboot_request = False
            connection = self.create_conn(host_name)
            channel = self.create_conn_chan(host_name, 'linux')

            #recv_buff = channel.exec_command(f'cat {grub2_cfg}')
            #if not recv_buff.count('hugepagesz=1G'):
            #    channel.exec_command(f"sed -i 's/linux16 \/vmlinuz-3.10.0-693.el7.x86_64 root=.*$/&default_hugepagesz=1G hugepagesz=1G hugepages=16/' {grub2_cfg}")
            #    reboot_request = True

            channel.exec_command(f'ethtool -K {pf_name} rxvlan off')
            channel.exec_command(f'ethtool -K {pf_name} txvlan off')
            channel.exec_command('modprobe i40evf')

            recv_buff = channel.exec_command(f'ethtool -i {pf_name}')
            # bus-info: 0000:3b:00.1
            bus_info = re.search(r'bus-info:\s+(\S+)', recv_buff).group(1)
            recv_buff = channel.exec_command(f'find /sys/devices -name sriov_numvfs | grep {bus_info} --color=never')
            # /sys/devices/pci0000:3a/0000:3a:00.0/0000:3b:00.1/sriov_numvfs
            config_path = re.search(r'[\r\n]+(\/sys\/devices\S+\/sriov_numvfs)', recv_buff).group(1)
            channel.exec_command(f'echo {vf_num} > {config_path}', timeout=66)
            channel.exec_command('lspci | grep Ethernet --color=never')
            # 3b:0a.0 Ethernet controller: Intel Corporation XL710/X710 Virtual Function (rev 02)
            # 3b:0a.1 Ethernet controller: Intel Corporation XL710/X710 Virtual Function (rev 02)
            # 3b:0a.2 Ethernet controller: Intel Corporation XL710/X710 Virtual Function (rev 02)
            # 3b:0a.3 Ethernet controller: Intel Corporation XL710/X710 Virtual Function (rev 02)

        '''
/opt/mellanox/iproute2/sbin/tc qdisc del dev vxlan1cx5 ingress 
        '''

    def iperf(self, server_conn='vm69188', client_conn='testbed', iperf_opt = '-u -l64 -b0 -R', port_num=24, server_ip=None, duration=120):
        self.port_list = [i for i in range(61000, 61000 + port_num)]
        
        if not server_ip:
            server_ip = self.conn_cfg[server_conn]['host']

        self.create_conn(server_conn)
        chan_server = self.create_conn_chan(server_conn, 'linux')

        self.create_conn(client_conn)
        chan_client = self.create_conn_chan(client_conn, 'linux')

        for port in self.port_list:
            self.create_conn_chan(client_conn, f"linux_{port}")
            chan_server.exec_command(f'iperf3 -s -p{port} -1 -D')

        #12000 #86400
        timeout = duration + 120
        time.sleep(1)

        # for port in self.port_list:
        port_num = len(self.port_list)
        for iii in range(port_num):
            port = self.port_list[iii]

            chan = self.conn_dict[client_conn].chan_dict[f"linux_{port}"]
            chan.log_on_screen = False

            go_thread(chan.exec_command,
                    args=(
                    f'timeout {duration} iperf3 -c {server_ip} -p{port} -i3 -t{duration} -P1 -Z --get-server-output {iperf_opt}',),  # 16 streams
                    kwargs={'timeout': timeout})

        go_thread(chan_server.exec_command, args=('sar -n DEV 3',), kwargs={'timeout': timeout}, wait_finish=False)
        go_thread(chan_client.exec_command, args=('sar -n DEV 3',), kwargs={'timeout': timeout}, wait_finish=False)

        go_thread.join_threads(timeout)
        self.threading_channel_end()

        time.sleep(1)
        chan_server.exec_command("ps -ef |grep iperf3 |awk '{print $2}'|xargs kill -9")

