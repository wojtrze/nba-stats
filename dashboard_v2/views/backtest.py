from core import backtest_view
from core.state import language
from core.ui import page_header
from i18n import t

page_header(t('bt.title', language()), t('bt.purpose', language()))
backtest_view.render()
