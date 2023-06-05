import datetime
import json
import os
import sys

LINEBREAK = '\n'
def file2list(filepath):
    ret = []
    with open(filepath, encoding='utf8', mode='r') as f:
        ret = [line.rstrip('\n') for line in f.readlines()]
    return ret
def list2file(filepath, ls):
    with open(filepath, encoding='utf8', mode='w') as f:
        f.writelines(['{:}\n'.format(line) for line in ls] )

def file2str(filepath):
    ret = ''
    with open(filepath, encoding='utf8', mode='r') as f:
        ret = f.read()
    return ret
def str2file(filepath, s):
    with open(filepath, encoding='utf8', mode='w') as f:
        f.write(s)
def str2dict(s):
    return json.loads(s)
def dict2str(d, **kwargs):
    return json.dumps(d, **kwargs)

def datestr2dow_eng(datestr):
    year, month, day = [int(elm) for elm in datestr.split('/')]
    dt = datetime.datetime(year=year, month=month, day=day)
    wd = dt.weekday()
    #dow_j = ['月',"火", "水", "木","金","土","日"][wd]
    dow_e = ['Mon',"Tue","Wed","Thu","Fri","Sat","Sun"][wd]
    return dow_e

def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('--input-scb', default=None)
    parser.add_argument('--data-json', default=None)
    parser.add_argument('--report-directory', default=None)

    args = parser.parse_args()
    return args

def abort(msg):
    print(f'Abort! {msg}')
    sys.exit(1)

class Timestamp:
    def __init__(self):
        self._dtobj = None

    def from_now(self):
        self._dtobj = datetime.datetime.today()

    def from_datestr(self, datestr):
        year, month, day = [int(elm) for elm in datestr.split('/')]
        dt = datetime.datetime(year=year, month=month, day=day)
        self._dtobj = dt

    def to_datestr(self):
        if not self._dtobj:
            raise RuntimeError('Timestamp object is not from() yet.')
        return self._dtobj.strftime('%Y/%m/%d')

    def minus_day(self, day):
        self._dtobj = self._dtobj - datetime.timedelta(days=day)

    @staticmethod
    def get_today_datestr():
        return datetime.datetime.today().strftime('%Y/%m/%d')

    @staticmethod
    def get_yesterday_datestr():
        dt = datetime.datetime.today()
        delta = datetime.timedelta(days=1)
        dt = dt - delta
        return dt.strftime('%Y/%m/%d')

    @staticmethod
    def get_latest_7days_as_datestr(datestr):
        timestamp = Timestamp()
        timestamp.from_datestr(datestr)
        datestrs = []
        for _ in range(7):
            datestrs.insert(0, timestamp.to_datestr())
            一日ずつ減らしていく = 1
            timestamp.minus_day(一日ずつ減らしていく)
        return datestrs

    @staticmethod
    def remove_day_from_datestr(datestr):
        l = len('yyyy/mm')
        return datestr[:l]

class ActionStore:
    '''
    以下は3-history
      action1 = ['2023/05/24', '2023/05/24', '2023/05/25']
    
    datestr
      'yyyy/mm/dd'
    '''
    def __init__(self):
        self._dict = {}

    def add(self, action_name, datestr):
        notfound = action_name not in self._dict
        if notfound:
            self._dict[action_name] = []
        history = self._dict[action_name]
        history.append(datestr)

    def get_count(self, action_name):
        notfound = action_name not in self._dict
        if notfound:
            return 0
        history = self._dict[action_name]
        return len(history)

    def _history_or_error(self, action_name):
        notfound = action_name not in self._dict
        if notfound:
            raise RuntimeError(f'action "{action_name}" not found.')
        history = self._dict[action_name]
        return history

    def get_daily_count(self, action_name, datestr_given):
        history = self._history_or_error(action_name)
        count = 0
        for datestr_in_history in history:
            if datestr_in_history==datestr_given:
                count += 1
        return count

    def get_weekly_count(self, action_name, datestr_given):
        history = self._history_or_error(action_name)

        latest_7days_datestrs = Timestamp.get_latest_7days_as_datestr(datestr_given)

        count = 0
        for datestr_in_history in history:
            for datestr_in_targetweek in  latest_7days_datestrs:
                if datestr_in_history==datestr_in_targetweek:
                    count += 1
                    break
        return count

    def get_monthly_count(self, action_name, datestr_without_day):
        history = self._history_or_error(action_name)

        count = 0
        for datestr_in_history in history:
            datestr_without_day_in_history = Timestamp.remove_day_from_datestr(datestr_in_history)
            a = datestr_without_day_in_history
            b = datestr_without_day
            if a==b:
                count += 1
        return count

    @property
    def actions(self):
        actions = []
        for k in self._dict:
            actionname = k
            history = self._dict[k]
            action = Action(actionname)
            action.replace_history(history)
            actions.append(action)
        return actions

class Action:
    def __init__(self, action_name):
        self._name = action_name
        self._history = []

    def add_datestr(self, datestr):
        self._history.append(datestr)

    def replace_history(self, history):
        self._history = history

    @property
    def name(self):
        return self._name
    
    @property
    def history(self):
        return self._history

class PostendDetector:
    def __init__(self, workspace_reader, workspace_writer):
        self._reader = workspace_reader
        self._writer = workspace_writer

    def postended_actions(self):
        lines = self._reader.lines
        actions = []
        for line in lines:
            postended, action = self.detect_postend(line)
            if not postended:
                self._writer.add_raw(line)
                continue
            actions.append(action)
            self._writer.add_from_actioname(action.name)
        return actions

    def detect_postend(self, line):
        ''' @retval (boolean, action)
        報告的終了されてないならFalse
        されてるならTrueで、かつActionも返す
        '''

        '''
        action(報告的終了していない)
        x action(今日1回した)
        y action(昨日1回した)
        xx action(今日2回した)

        xxx action
        ^^^ ^^^^^^    1: mark
        1     2       2: action name
        '''

        NOT_POSTENDED = False
        POSTENDED = True
        ACTION_DO_NOT_CARE = None

        is_empty_line = len(line.strip())==0
        if is_empty_line:
            return (NOT_POSTENDED, ACTION_DO_NOT_CARE)
        space_not_found = line.find(' ')==-1
        if space_not_found:
            return (NOT_POSTENDED, ACTION_DO_NOT_CARE)
        no_mark = line[0]!='x' and line[0]!='y'
        if no_mark:
            return (NOT_POSTENDED, ACTION_DO_NOT_CARE)
        no_mark_and_actionname = len(line)<=2
        if no_mark_and_actionname:
            return (NOT_POSTENDED, ACTION_DO_NOT_CARE)

        splitは最初の一回だけやる=1
        marks, action_name = line.split(' ', splitは最初の一回だけやる)
        action = Action(action_name)

        todaystr = Timestamp.get_today_datestr()
        yesterdaystr = Timestamp.get_yesterday_datestr()
        for c in marks:
            if c=='x':
                action.add_datestr(todaystr)
                continue
            if c=='y':
                action.add_datestr(yesterdaystr)
                continue

        return (POSTENDED, action)

class WorkspaceReader:
    def __init__(self):
        self._lines = []

    def parse(self, obj):
        raise NotImplementedError()

    @property
    def lines(self):
        return self._lines

class FileWorkspaceReader(WorkspaceReader):
    def __init__(self):
        super().__init__()

    def parse(self, obj):
        filename = obj
        lines = file2list(filename)
        self._lines = lines

class WorkspaceWriter:
    def __init__(self):
        self._lines = []

    def add_raw(self, line):
        self._lines.append(line)

    def add_from_actioname(self, action_name):
        line = f' {action_name}'
        self._lines.append(line)

    def save(self, obj):
        raise NotImplementedError()

    @property
    def lines(self):
        return self._lines

class FileWorkspaceWriter(WorkspaceWriter):
    def __init__(self):
        super().__init__()

    def save(self, obj):
        filename = obj
        list2file(filename, self._lines)

class ActionStorage:
    def __init__(self, d):
        self._dict = d

    @staticmethod
    def from_jsonstring(jsonstr):
        is_empty_or_white = len(jsonstr.strip())==0
        if is_empty_or_white:
            d = {}
        else:
            d = json.loads(jsonstr)
        actionstorage = ActionStorage(d)
        return actionstorage

    @staticmethod
    def from_actionstore(actionstore):
        actions = actionstore.actions
        d = {}
        for action in actions:
            name = action.name
            history = action.history
            d[name] = history
        actionstorage = ActionStorage(d)
        return actionstorage

    def to_actionstore(self):
        actionstore = ActionStore()
        for k in self._dict:
            actionname = k
            history = self._dict[k]
            for datestr in history:
                actionstore.add(actionname, datestr)
        return actionstore

    def to_jsonstring_pretty(self, indent):
        s = json.dumps(self._dict, indent=indent, sort_keys=True, ensure_ascii=False)
        return s

class Report:
    def __init__(self, actionstore):
        self._actionstore = actionstore
        self._parse()

    def _parse(self):
        acst = self._actionstore

        datestrs = []
        for action in acst.actions:
            for datestr in action.history:
                datestrs.append(datestr)
        datestrs.sort()
        self._lower_datestr = datestrs[0]
        self._upper_datestr = datestrs[-1]
        self._count_total = len(datestrs)

        datestrs_without_duplicate = sorted(list(set(datestrs)))

        '''
        2023/02/11
         [action1, 2],
         [action2, 1],
         [action3, 4],
        '''
        datestr_actionname_dict = {}

        for datestr in datestrs_without_duplicate:
            for action in acst.actions:
                count = 0
                for datestr_of_action in action.history:
                    if datestr==datestr_of_action:
                        count += 1
                if count==0:
                    continue
                k = datestr
                notfound = not k in datestr_actionname_dict
                if notfound:
                    datestr_actionname_dict[k] = []
                v = [action.name, count]
                datestr_actionname_dict[k].append(v)
        self._dailycounts = datestr_actionname_dict

        '''
        weekは土曜日基点にする。
        日曜日に週次レビューを行う場合、見たいのは先週日曜日から今週土曜日まで。
        '''
        weekly_target_datestrs = []
        for datestr in datestrs_without_duplicate:
            year, month, day = [int(x) for x in datestr.split('/')]
            dt = datetime.datetime(year=year, month=month, day=day)
            wd = dt.weekday()
            #SUN = 6
            SAT = 5
            if wd!=SAT:
                continue
            weekly_target_datestrs.append(datestr)
        datestr_actionname_dict = {}
        for sunday_datestr in weekly_target_datestrs:
            for action in acst.actions:
                count = acst.get_weekly_count(action.name, sunday_datestr)
                if count==0:    
                    continue
                k = sunday_datestr
                notfound = not k in datestr_actionname_dict
                if notfound:
                    datestr_actionname_dict[k] = []
                v = [action.name, count]
                datestr_actionname_dict[k].append(v)
        self._weeklycounts = datestr_actionname_dict

        monthly_datestrs = []
        for datestr in datestrs_without_duplicate:
            l = len('yyyy/mm')
            monthpart = datestr[:l]
            monthly_datestrs.append(monthpart)
        monthly_datestrs_without_duplicate = sorted(list(set(monthly_datestrs)))
        datestr_actionname_dict = {}
        for monthly_datestr in monthly_datestrs_without_duplicate:
            for action in acst.actions:
                count = acst.get_monthly_count(action.name, monthly_datestr)
                if count==0:
                    continue
                k = monthly_datestr
                notfound = not k in datestr_actionname_dict
                if notfound:
                    datestr_actionname_dict[k] = []
                v = [action.name, count]
                datestr_actionname_dict[k].append(v)
        self._monthlycounts = datestr_actionname_dict

    @property
    def dailycounts(self):
        return self._dailycounts
    @property
    def weeklycounts(self):
        return self._weeklycounts
    @property
    def monthlycounts(self):
        return self._monthlycounts

    @property
    def lower_datestr(self):
        return self._lower_datestr

    @property
    def upper_datestr(self):
        return self._upper_datestr

    @property
    def count_total(self):
        return self._count_total

class FileReport:
    def __init__(self, report):
        self._report = report
        self._parse()

    def _parse(self):
        self._daily()
        self._weekly()

    @staticmethod
    def sort_to_most_counted(action_count_pairs):
        out = sorted(action_count_pairs, key=lambda elm:elm[1])
        out.reverse()
        return out

    def _lines_by_DescOrder_and_MostCounted(self, xxxxcounts):
        outlines = []

        datestrs = []
        for datestr in xxxxcounts:
            datestrs.append(datestr)
        datestrs.sort()
        # 最新日を上に書きたいので降順にする
        datestrs.reverse()

        for datestr in datestrs:
            dow = datestr2dow_eng(datestr)
            action_count_pairs = xxxxcounts[datestr]
            total = 0
            for pair in action_count_pairs:
                _, count = pair
                total += count
            out = f'{datestr} {dow} {total}'
            outlines.append(out)

            INDENT = ' '
            BLANK_LINE = ''
            pairs = self.sort_to_most_counted(action_count_pairs)
            for pair in pairs:
                name, count = pair
                out = f'{INDENT}{count} {name}'
                outlines.append(out)
            outlines.append(BLANK_LINE)

        return outlines

    def _daily(self):
        outlines = self._lines_by_DescOrder_and_MostCounted(self._report.dailycounts)
        self._dailycounts_by_lines = outlines

    def _weekly(self):
        outlines = self._lines_by_DescOrder_and_MostCounted(self._report.weeklycounts)
        self._weeklycounts_by_lines = outlines

    @property
    def dailycounts_by_lines(self):
        return self._dailycounts_by_lines

    @property
    def weeklycounts_by_lines(self):
        return self._weeklycounts_by_lines

if __name__ == "__main__":
    args = parse_arguments()

    input_filename = args.input_scb
    datajson_filename = args.data_json
    report_directory = args.report_directory

    if not os.path.exists(input_filename):
        abort(f'input-scb invalid: {input_filename}')
    if not os.path.exists(report_directory):
        abort(f'report-directory invalid: {report_directory}')
    if not os.path.exists(datajson_filename):
        emptyfile = []
        list2file(datajson_filename, emptyfile)

    ws_reader = FileWorkspaceReader()
    ws_writer = FileWorkspaceWriter()
    ws_reader.parse(input_filename)
    detector = PostendDetector(ws_reader, ws_writer)
    postended_actions = detector.postended_actions()

    jsonstr = file2str(datajson_filename)
    actionstorage = ActionStorage.from_jsonstring(jsonstr)
    out_actionstore = actionstorage.to_actionstore()
    for action in postended_actions:
        print(f'{action.name}: {action.history}')
        for datestr in action.history:
            out_actionstore.add(action.name, datestr)
    out_actionstorage = ActionStorage.from_actionstore(out_actionstore)

    ws_writer.save(input_filename)
    out_jsonstr = out_actionstorage.to_jsonstring_pretty(indent=2)
    str2file(datajson_filename, out_jsonstr)

    report = Report(out_actionstore)
    filereport = FileReport(report)
    dailyfile_fullpath = os.path.join(report_directory, 'counte_daily.scb')
    list2file(dailyfile_fullpath, filereport.dailycounts_by_lines)
    weeklyfile_fullpath = os.path.join(report_directory, 'counte_weekly.scb')
    list2file(weeklyfile_fullpath, filereport.weeklycounts_by_lines)
