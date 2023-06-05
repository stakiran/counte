# coding: utf-8

import unittest
import datetime

import counte

class TestTimerstamp(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test(self):
        timestamp = counte.Timestamp()
        timestamp.from_now()
        correct_datestr = datetime.datetime.today().strftime('%Y/%m/%d')
        self.assertEqual(timestamp.to_datestr(), correct_datestr)

        timestamp = counte.Timestamp()
        timestamp.from_datestr('2023/01/01')
        self.assertEqual(timestamp.to_datestr(), '2023/01/01')

        timestamp = counte.Timestamp()
        with self.assertRaises(RuntimeError):
            timestamp.to_datestr()

    def testWeeklyEnum(self):
        a = counte.Timestamp.get_latest_7days_as_datestr('2023/02/12')
        e = [
            '2023/02/06',
            '2023/02/07',
            '2023/02/08',
            '2023/02/09',
            '2023/02/10',
            '2023/02/11',
            '2023/02/12',
        ]
        self.assertListEqual(a, e)

    def testDatestrRemove(self):
        a = counte.Timestamp.remove_day_from_datestr('2023/02/01')
        e = '2023/02'
        self.assertEqual(a, e)

class TestActionStore(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test1(self):
        actionstore = counte.ActionStore()
        acst = actionstore

        self.assertEqual(acst.get_count('not found'), 0)

        acst.add('action1', '2023/05/24')
        self.assertEqual(acst.get_count('action1'), 1)

        acst.add('action1', '2023/05/23')
        self.assertEqual(acst.get_count('action1'), 2)

        acst.add('action1', '2023/05/23')
        self.assertEqual(acst.get_count('action1'), 3)

        acst.add('action1', '2022/01/01')
        acst.add('action1', '2024/12/31')
        self.assertEqual(acst.get_count('action1'), 5)

    def test2(self):
        actionstore = counte.ActionStore()
        acst = actionstore

        '''
              February       
         Su Mo Tu We Th Fr Sa
                   1  2  3  4
          5  6  7  8  9 10 11
         12 13 14 15 16 17 18
         19 20 21 22 23 24 25
         26 27 28            
        '''

        acst.add('action1', '2023/02/01')
        acst.add('action1', '2023/02/02')
        acst.add('action1', '2023/02/02')

        acst.add('action1', '2023/02/06')
        acst.add('action1', '2023/02/07')
        acst.add('action1', '2023/02/08')
        acst.add('action1', '2023/02/09')
        acst.add('action1', '2023/02/10')
        acst.add('action1', '2023/02/11')
        acst.add('action1', '2023/02/11')
        acst.add('action1', '2023/02/12')

        acst.add('action1', '2023/03/01')

        with self.assertRaises(RuntimeError):
            acst.get_daily_count('not found', '2023/02/01')
            acst.get_weekly_count('not found', '2023/02/01')
            acst.get_monthly_count('not found', '2023/02')

        self.assertEqual(acst.get_daily_count('action1', '2023/02/01'), 1)
        self.assertEqual(acst.get_daily_count('action1', '2023/02/02'), 2)
        self.assertEqual(acst.get_daily_count('action1', '2023/02/03'), 0)

        # weekly は過去7日分をカウントする
        self.assertEqual(acst.get_weekly_count('action1', '2023/02/12'), 8)
        self.assertEqual(acst.get_weekly_count('action1', '2023/02/26'), 0)

        self.assertEqual(acst.get_monthly_count('action1', '2023/02'), 11)
        self.assertEqual(acst.get_monthly_count('action1', '2023/03'), 1)
        self.assertEqual(acst.get_monthly_count('action1', '2023/04'), 0)

class MockWorkspaceReader(counte.WorkspaceReader):
    def __init__(self):
        super().__init__()

    def parse(self, obj):
        s = obj
        lines = s.split(counte.LINEBREAK)
        outlines = []
        for line in lines:
            is_empty_or_white = len(line.strip())==0
            if is_empty_or_white:
                continue
            outlines.append(line)
        self._lines = outlines

class MockWorkspaceWriter(counte.WorkspaceWriter):
    def __init__(self):
        super().__init__()

    def save(self):
        pass

class TestPostendDetector(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test(self):
        testdata = '''
 action
x action1
xx action2
y action-y1
xy action1-y1
yxxy action2-y2
'''
        T = counte.Timestamp.get_today_datestr()
        Y = counte.Timestamp.get_yesterday_datestr()

        ws_reader = MockWorkspaceReader()
        ws_writer = MockWorkspaceWriter()
        ws_reader.parse(testdata)
        detector = counte.PostendDetector(ws_reader, ws_writer)
        actions = detector.postended_actions()

        self.assertEqual(len(actions), 5)
        action1 = actions[0]
        action2 = actions[1]
        action_y1 = actions[2]
        action1_y1 = actions[3]
        action2_y2 = actions[4]
        self.assertEqual(action1.name, 'action1')
        self.assertListEqual(action1.history, [T])
        self.assertEqual(action2.name, 'action2')
        self.assertListEqual(action2.history, [T, T])
        self.assertEqual(action_y1.name, 'action-y1')
        self.assertListEqual(action_y1.history, [Y])
        self.assertEqual(action1_y1.name, 'action1-y1')
        self.assertListEqual(action1_y1.history, [T, Y])
        self.assertEqual(action2_y2.name, 'action2-y2')
        self.assertListEqual(action2_y2.history, [Y, T, T, Y])

        ws_writer.save()
        writee_lines = ws_writer.lines
        LENGTH_OF_TESTDATA_WITHOUT_BLANKLINE = 6
        self.assertEqual(len(writee_lines), LENGTH_OF_TESTDATA_WITHOUT_BLANKLINE)
        self.assertEqual(writee_lines[0], ' action')
        self.assertEqual(writee_lines[1], ' action1')
        self.assertEqual(writee_lines[2], ' action2')
        self.assertEqual(writee_lines[3], ' action-y1')
        self.assertEqual(writee_lines[4], ' action1-y1')
        self.assertEqual(writee_lines[5], ' action2-y2')

class TestActionStorage(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test(self):
        testdata = '''{
  "action1" : [
    "2023/05/28"
  ],
  "action2" : [
    "2023/05/28",
    "2023/05/27"
  ],
  "action3" : [
    "2023/05/28",
    "2023/05/28",
    "2023/05/28",
    "2023/05/27"
  ]
}'''
        actionstorage = counte.ActionStorage.from_jsonstring(testdata)

        actionstore = actionstorage.to_actionstore()
        self.assertEqual(actionstore.get_count('action1'), 1)
        self.assertEqual(actionstore.get_count('action2'), 2)
        self.assertEqual(actionstore.get_daily_count('action3', '2023/05/28'), 3)

        actionstore.add('action1','2023/06/01')
        actionstore.add('action2','2023/05/28')
        actionstore.add('action4','2023/06/01')
        actionstore.add('action4','2023/06/02')
        actionstore.add('action0','2023/06/01')

        actionstorage = counte.ActionStorage.from_actionstore(actionstore)
        actual = actionstorage.to_jsonstring_pretty(indent=2)
        # expect は内部的には json.dumps の仕様に従うしかない。
        # たとえば key 名の次の : との間にはスペースが無い、とか。
        expect = '''{
  "action0": [
    "2023/06/01"
  ],
  "action1": [
    "2023/05/28",
    "2023/06/01"
  ],
  "action2": [
    "2023/05/28",
    "2023/05/27",
    "2023/05/28"
  ],
  "action3": [
    "2023/05/28",
    "2023/05/28",
    "2023/05/28",
    "2023/05/27"
  ],
  "action4": [
    "2023/06/01",
    "2023/06/02"
  ]
}'''
        self.assertEqual(expect, actual)

    def test_from_empty(self):
        emptystring = ''
        counte.ActionStorage.from_jsonstring(emptystring)

class TestReport(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test(self):
        actionstore = counte.ActionStore()
        acst = actionstore

        '''
              February       
         Su Mo Tu We Th Fr Sa
                   1  2  3  4
          5  6  7  8  9 10 11
         12 13 14 15 16 17 18
         19 20 21 22 23 24 25
         26 27 28            
        '''

        acst.add('action1', '2023/02/01')
        acst.add('action1', '2023/02/02')
        acst.add('action1', '2023/02/02')
        acst.add('action1', '2023/02/06')
        acst.add('action1', '2023/02/07')
        acst.add('action1', '2023/02/08')
        acst.add('action1', '2023/02/09')
        acst.add('action1', '2023/02/10')
        acst.add('action1', '2023/02/11')
        acst.add('action1', '2023/02/11')
        acst.add('action1', '2023/02/12')
        acst.add('action1', '2023/03/01')

        acst.add('action2', '2023/02/07')
        acst.add('action2', '2023/02/08')
        acst.add('action2', '2023/02/09')
        acst.add('action2', '2023/02/10')
        acst.add('action2', '2023/02/11')
        acst.add('action2', '2023/02/12')
        acst.add('action2', '2023/02/13')

        acst.add('action3', '2023/03/03')

        report = counte.Report(actionstore)

        self.assertEqual(report.lower_datestr, '2023/02/01')
        self.assertEqual(report.upper_datestr, '2023/03/03')

        self.assertEqual(report.count_total, 20)

        '''
        テスト書かなくてもいいかも、純粋にきついので
        あるいは dailyactions とかの中身見る前までにする

        2023/02/11
         action1: 2,  dailycountあるし、こっちいけるだろ
         action2: 1,
        2023/02/11
         action1, action1, action2
        
        2023/02/05
         action1: 3
        2023/02/12
         action1: 8
         action2: 7
        '''

        report.dailycounts
        report.weeklycounts
        report.monthlycounts

if __name__ == '__main__':
    unittest.main()
