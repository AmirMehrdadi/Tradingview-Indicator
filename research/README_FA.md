# فاز ۱ — Loader توسعه و Stage-0A

مرجع: `STRATEGY_SPEC_v0.2.2.md` در تگ `v0.2.2-design`، commit برابر `ac8fc4bb9b66a59c7224aaec1630a594b41d7e80`. سند و تگ تغییر نمی‌کنند. این فاز فقط توصیفی است؛ K تعیین نمی‌شود و پژوهش سودآوری، Stage-0B، Selection و Pine در آن وجود ندارند.

از ریشه مخزن، با Python 3.9 یا جدیدتر اجرا کنید. اجرای حاضر با Python 3.9.6 بررسی می‌شود. همه وابستگی‌ها از کتابخانه استانداردند؛ نصب SDK یا اتصال حساب لازم نیست. تنظیمات در `configs/stage0a.json` قرار دارند و این فاز تغییر سال/نماد/مدل هزینه یا K را نمی‌پذیرد.

```sh
python3 -m unittest discover -s tests -v
python3 -m research fetch
```

`fetch` ابتدا metadata جاری و سپس چهار دیتاست 15m/1h سال‌های ۲۰۲۳ و ۲۰۲۴ را دریافت می‌کند. هر سال anchor مستقل ۶۰ ساعت قبل از اول ژانویه دارد؛ برای ۲۰۲۳ از `2022-12-29T12:00:00Z` و برای ۲۰۲۴ از `2023-12-29T12:00:00Z`. پایان هر درخواست API یک میلی‌ثانیه پیش از انتهای بازه نیمه‌باز مجاز است. ۲۰۲۵ به بعد، Holdout، Funding، Mark و endpointهای حساب/سفارش در allowlist نیستند. metadata جاری ابزار تنها استثنای زمانی صریح درخواست کاربر است و هیچ تاریخچه قیمت جدیدی نیست.

درخواست‌ها فقط GET عمومی به `https://api.bybit.com` و دو endpoint مستند هستند: [Kline](https://bybit-exchange.github.io/docs/v5/market/kline) و [Instruments Info](https://bybit-exchange.github.io/docs/v5/market/instrument). پنجره‌ها حداکثر ۱۰۰۰ کندل دارند؛ ترتیب نزولی پاسخ مرتب و duplicate یکسان حذف می‌شود. duplicate متعارض قرنطینه می‌شود. حداکثر ۲۵۶ تلاش شبکه، سه تلاش برای هر درخواست، timeout پانزده ثانیه و backoff محدود اعمال می‌شود. HTTP 403 و سایر خطاهای غیرقابل retry نهایی‌اند؛ تغییر میزبان برای دورزدن محدودیت، redirect و خاموش‌کردن TLS وجود ندارد.

شناسه run در خروجی چاپ می‌شود. داده و manifest در `data/stage0a/<RUN_ID>/` و گزارش در `reports/stage0a/<RUN_ID>/` هستند. داده‌های حجیم در Git ignore شده‌اند؛ این به معنی حذف فایل‌های محلی نیست. هر درخواست URL/زمان UTC/hash پاسخ دارد؛ هر CSV و manifest، SHA-256 دارد. metadata جاری با `HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION` ذخیره می‌شود؛ اعتبار تاریخی و minimum خروج reduce-only تأیید نشده و در این فاز quantity/exits استفاده نمی‌شود.

بازاجرای بدون شبکه از همان Cache:

```sh
python3 -m research analyze --run-id RUN_ID
```

RUN_ID را با شناسه واقعی جایگزین کنید. مسیر دلخواه، traversal و symlink پذیرفته نیستند. بازه، phase، spec/config و hashها قبل از مصرف قیمت بررسی می‌شوند. Cache مصنوعی یا قرنطینه‌شده برای پژوهش واقعی رد می‌شود. تحلیل مستقل هر سال فقط با 15m و 1h کامل و metadata لازم انجام می‌شود. سال ناقص `NOT_RUN` است؛ قیمت missing با صفر یا forward-fill ترمیم نمی‌شود. خطای metadata مشترک، اجرای هر دو سال را متوقف می‌کند. کد خروج ۲ به معنای مسدود/ناقص‌بودن عملیات است، نه شکست سودآوری.

فایل‌های خروجی:

- `run_manifest.json`: منشأ، hashها، runtime، تمام درخواست‌ها و مانع‌های دریافت.
- `*.csv.manifest.json`: محدوده مجاز، کیفیت، missing/invalid/duplicate/incomplete و hash دیتاست.
- `instrument.json`: snapshot واقعی metadata جاری، در صورت دسترسی.
- `2023.json` و `2024.json`: شمارش، کیفیت و صدک‌های توصیفی، یا `NOT_RUN` با علت و آمار null.
- `*_opportunities.csv`: فرصت‌های خام و مراحل پیوت/Stop؛ فقط در سال معتبر.
- `quality.json`، `analysis_provenance.json` و `summary_FA.md`: کیفیت، منشأ محاسبات و گزارش فارسی.

فرصت خام با معامله پذیرفته‌شده یکسان نیست. بدون K، Stop/TP fill، quantity، daily gate، عدم هم‌پوشانی و مصرف Pullback اجرا نمی‌شوند؛ یک Pullback می‌تواند چند فرصت خام داشته باشد. هیچ خروج، fee تحقق‌یافته، بازده، win rate، PF، Expectancy، DD یا Bootstrap محاسبه نمی‌شود. ATR/Stop/هزینه مربوط به اطلاعات همان Close هستند و پیوت فقط پس از سه کندل سمت راست در دسترس است. آخرین پیوت مناسب با سن حداکثر ۸۰ کندل و تأیید در/قبل از سیگنال انتخاب می‌شود.

ATR% روی همه کندل‌های بسته با Open داخل سال گزارش می‌شود. مالکیت فرصت بر Close در `[year_start,year_end)` است؛ سیگنال احتمالی در Close دقیق شروع سال از آخرین کندل Warm-up مجاز است. هر دو تعریف در گزارش از هم جدا هستند. صدک‌های ۵، ۱۰، ۲۵، ۵۰، ۷۵، ۹۰ و ۹۵ type-7 هستند؛ جامعه خام، دارای پیوت و Stop معتبر و Long/Short جدا ثبت می‌شوند. EMA از نخستین Close anchor و ATR با seed میانگین ۱۴ TR آغاز می‌شود.

هزینه پایه صرفاً فرض سند است: fee برابر ۰٫۰۵۵٪ هر سمت و friction برابر ۰٫۰۲٪؛ proxy `(entry_ref+SL)*(fee+friction)` بدون Funding. tick از metadata واقعی گرفته می‌شود و حدس زده نمی‌شود. نسبت `planned_risk_price / roundtrip_cost_per_btc` توصیف می‌شود؛ هیچ عدد K پیشنهاد، بهینه یا freeze نمی‌شود.

خروجی محاسباتی روی ورودی یکسان قطعی است. timestampهای دریافت شبکه برای هر دریافت جدید متفاوت‌اند و جدا از hash محتوای کندل/خروجی محاسباتی ثبت می‌شوند. بازاجرای همان Cache/کد/config خروجی یکسان می‌دهد. گزارش متفاوتِ ازقبل‌موجود overwrite نمی‌شود؛ در تغییر کد، گزارش قبلی را حفظ و ارزیابی جدید را در نسخه/run مستقل مدیریت کنید.

آزمون‌ها از fixtureهای مصنوعی صریح و TemporaryDirectory استفاده می‌کنند. هیچ‌یک شاهد بازار واقعی یا اجرای TradingView نیستند. گیت قفل پارامتر پژوهشی، K و تمام Execution Gateها باز باقی می‌مانند. انتخاب انسانی K پس از مشاهده توزیع‌های معتبر و سپس ثبت rationale/config/commit، کار مرحله بعد است.
