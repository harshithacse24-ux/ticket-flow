import unittest
from ml_engine import classify_ticket, find_kb_solution, search_knowledge_base
class TicketFlowTests(unittest.TestCase):
 def test_login(self): self.assertEqual(classify_ticket('forgot password cannot login portal')[0],'Account/Login')
 def test_wifi_kb(self):
  t='campus wifi network cannot connect internet'; c,_=classify_ticket(t); self.assertEqual(c,'Network')
  s,source=find_kb_solution(t,c); self.assertIsNotNone(s); self.assertEqual(source,'Campus Wi-Fi Troubleshooting')
 def test_hardware(self): self.assertEqual(classify_ticket('laptop keyboard broken')[0],'Hardware')
 def test_software(self): self.assertEqual(classify_ticket('application crashes when I open it')[0],'Software')
 def test_kb_search(self): self.assertTrue(search_knowledge_base('forgot password portal'))
if __name__=='__main__': unittest.main(verbosity=2)
