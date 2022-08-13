# qinhuawei@outlook.com
import os,json,logging,argparse,importlib,time,sys,traceback,coloredlogs
sys.path.insert(0, '')

if os.name == 'nt':
    fcntl = None
else:
    import fcntl

def load_json_file(file_name):
    try:
        contents = open(file_name).read()
        return eval(contents)
    except:
        data_file = open(file_name, 'r')
        json_data = json.load(data_file)
        data_file.close()
        return json_data

def load_csv_file(csv_file):
    with open(csv_file) as f:
        return f.readlines()

def load_conn_file(file_name):
    if file_name.endswith('.csv'):
        return load_csv_file(file_name)
    else:
        return load_json_file(file_name)

def exception(trace):
    type, value, tb = sys.exc_info()
    try:
        logging.error('TYPE={}, VALUE=[{}]'.format(type,value[0]))
    except:
        logging.error('TYPE={}, VALUE=[{}]'.format(type,value))
    stack_info = ''.join(traceback.format_tb(tb))
    logging.error('%s\n%s' %(trace, stack_info))
    try:
        logging.error(value[1])
    except:
        pass

if __name__ == "__main__":
    ts_start = time.time()

    parser_t = argparse.ArgumentParser(description="UAS = Unified Automation System. qinhuawei@outlook.com")
    parser_t.add_argument('-r', dest='case', type=str, required=True, help='case.path')
    parser_t.add_argument('-R', dest='regression', type=int, required=False, default=1,  help='Regression mode. If not set, case would wait when error.')
    parser_t.add_argument('-l', dest='log_folder', type=str, required=False, help='default is log/<case>_<yymmdd_HHMMSS>',)
    parser_t.add_argument('-e', dest='execute', type=str, required=False, help='demo.execute()',)
    parser_t.add_argument('-o', dest='option_quote', type=str, required=False, help='execute("option")',)
    parser_t.add_argument('-O', dest='option', type=str, required=False, help='execute(option)',)
    parser_t.add_argument('-s', dest='show_functions', action='store_true', help='show functions in the case',)
    parser_t.add_argument('-c', dest='conn_config', type=str, required=False, default='connection.json', help='connection.json')
    parser_t.add_argument('-p', dest='case_param', type=str, required=False, help='case_parameters.json', default='case_parameters.json')
    parser_t.add_argument('-v', dest='verbose', type=int, required=False, default=1, choices=[0,1,2], help='0=hide log, 1=log on screen, 2=paramiko debug, default=1',)
    args = parser_t.parse_args()

    log_folder = args.log_folder or 'log/%s_%s' %(args.case, time.strftime('%y%m%d_%H%M%S'))

    if args.execute:
        log_folder = f"log/{args.case}.{args.execute}_{time.strftime('%y%m%d_%H%M%S')}"

    logFormatter = logging.Formatter("%(asctime)s.%(msecs)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    if 2 != args.verbose:
        logging.getLogger("paramiko").setLevel(logging.WARNING)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    if args.verbose == 1:
        coloredlogs.install(logger=rootLogger, level='INFO',fmt='%(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s')
    elif args.verbose == 2:
        coloredlogs.install(logger=rootLogger, level='DEBUG',fmt='%(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s')
    else:
        coloredlogs.install(logger=rootLogger, level='CRITICAL',fmt='%(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s')

    try:
        if fcntl:
            fp = open('.uas.lock', 'w')
            fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logging.critical("uas is running. exit.")
        raise Exception('uas is running. exit.')

    case_module = importlib.import_module('%s.case' % (args.case))

    case_folder = os.path.dirname(os.path.abspath(case_module.__file__))
    if os.path.isfile('%s/%s' % (case_folder,args.conn_config)):
        args.conn_config = '%s/%s' % (case_folder,args.conn_config)
    elif os.path.isfile('%s/../%s' %(case_folder,args.conn_config)):
        args.conn_config = '%s/../%s' % (case_folder,args.conn_config)
    elif os.path.isfile('../%s' %(args.conn_config)):
        args.conn_config = '../%s' % (args.conn_config)
    elif not os.path.isfile(args.conn_config):
        logging.critical('%s not exist!' % (args.conn_config))
        sys.exit(-1)

    try:
        connection_config   = load_conn_file(args.conn_config)
        if os.path.isfile(args.case_param):
            try:
                case_parameters = load_json_file(args.case_param)
            except:
                logging.exception('=============load_json_file failed %s================' % (args.case_param))
                sys.exit(-1)
        else:
            case_parameters = {}

        test_case = case_module.uas_case(connection_config, case_parameters, log_folder, log_on_screen=args.verbose)
        test_case.case_path = os.path.dirname(case_module.__file__)
        test_case.case_name = args.case

        if args.show_functions:
            print(dir(test_case))
            import sys
            sys.exit(0)

        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        fileHandler = logging.FileHandler("{}/uas_main.log".format(log_folder))
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)
        logging.critical     ('====UAS START, regression {} ============'.format(args.regression))
        logging.exception = exception
        if args.execute:
            if args.option_quote:
                exec_string = 'test_case.{}("{}")'.format(args.execute,args.option_quote)
            elif args.option:
                exec_string = 'test_case.{}({})'.format(args.execute,args.option)
            else:
                exec_string = 'test_case.{}()'.format(args.execute)
            logging.info(exec_string)
            exec(exec_string)
        else:
            test_case.run()
    except KeyboardInterrupt:
        logging.critical     ('========= Ctrl+C =========')
    except Exception as inst:
        logging.exception   ('====UAS run FAILED =======')
        test_case.case_result = '{}'.format(inst.args[0])

        if not args.regression:
            try:
                choice = ''
                while choice != 'y':
                    choice=input('Continue to cleanup (y/n/pDB):').lower()
                    if choice == 'p':
                        import pdb
                        traceback.print_exc()
                        pdb.set_trace()
            except:
                pass

    try:
        if not args.execute:
            logging.critical     ('====UAS cleanup =========')
            test_case.case_cleanup()
    except Exception as inst:
        logging.exception   ('====UAS cleanup FAILED =======')
        if test_case.case_result is None:
            test_case.case_result = 'CLEANUP-%s' %inst.args[0]
    finally:
        try:
            test_case.end()
        except Exception as inst:
            logging.exception   ('====UAS end FAILED ========')
            if test_case.case_result is None:
                test_case.case_result = 'END-%s' %inst.args[0]

    duration = '%.1fS' %(time.time()-ts_start)
 
    if not test_case.case_result:
        test_case.case_result = 'PASS'
        coloredlogs.install(logger=rootLogger, level='DEBUG')
        logging.warning('====UAS [%s] [%s] [%s] [%s]' %(test_case.case_result, duration, args.case, log_folder))
    else:
        test_case.case_result = 'FAIL, %s' %test_case.case_result[:100]
        logging.critical('====UAS [%s] [%s] [%s] [%s]' %(test_case.case_result, duration, args.case, log_folder))

    fd = open('results.log', 'a')
    fd.write('%40s,%20s,%7s, %s\n' %(log_folder,args.case,duration,test_case.case_result))
    fd.close()
    #if os.name == 'nt' and test_case.case_result != 'PASS':
    #    os.startfile(os.path.join(os.path.dirname(os.path.realpath(__file__)),log_folder))
    if test_case.case_result.startswith('FAIL'):
        sys.exit(-1)
