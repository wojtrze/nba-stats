from core import backtest_view
from core.ui import page_header

page_header("Backtest 2022/23", "Today's props model on Unibet's 2022/23 player lines: how it would have done, a "
                                "strategy tester for any slice of those lines, and how each player's lines resolved.")
backtest_view.render()
