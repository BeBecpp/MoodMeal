# MoodMeal AI

MoodMeal AI нь гэрийн гал тогоонд зориулсан дулаахан, ойлголттой жорын вэб апп юм. Сэтгэл санаа, гэрт байгаа орц, цаг агаар, хооллох цаг зэргийг харгалзан SQLite дахь жорын сан, TheMealDB болон **Google Gemini 2.5 Flash** загвараар санал өгнө.

## Онцлог

- Монгол хэл дээрх орчинтой форм ба үр дүн
- SQLite + Flask-SQLAlchemy — орц, жор, хадгалсан жор
- Эхлээд локаль жор тааруулах (`recipe_match_service`)
- Сул тааруулалтанд TheMealDB (нэг орцоор хайлт, үр дүнг нэгтгэх)
- Эцсийн жорыг **Gemini 2.5 Flash** (`google-genai`) JSON горимд үүсгэнэ
- `GEMINI_API_KEY` байхгүй эсвэл алдаа гарвал **mock** жороор үргэлжлэнэ

## Шаардлага

- Python 3.9+

## Суулгах

```bash
cd moodmeal_ai
python -m venv venv
```

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

```bash
pip install -r requirements.txt
copy .env.example .env
```

(macOS/Linux дээр: `cp .env.example .env`)

## Өгөгдлийн сан суулгах

```bash
python seed.py
```

`seed.py` нь `ingredients`, `recipes`, `recipe_ingredients` хүснэгтүүдийн өгөгдлийг аюулгүйгээр цэвэрлээд дахин бөөнөөр оруулна. `saved_recipes` хүндэтгэн хөндөхгүй.

## Ажиллуулах

```bash
set FLASK_APP=app.py
flask run
```

(macOS/Linux: `export FLASK_APP=app.py`)

Дараа нь хөтөч дээр `http://127.0.0.1:5000` нээнэ үү.

## GEMINI_API_KEY нэмэх

`.env` файлд:

```
GEMINI_API_KEY=таны_түлхүүр
GEMINI_MODEL=gemini-2.5-flash
```

Түлхүүргүй үед апп ажиллана — mock жор гарна.

## Gemini 2.5 Flash ажиллаж байгааг шалгах

1. `GEMINI_API_KEY` тохируулна.
2. Нүүр хуудаснаас жор үүсгэнэ.
3. Үр дүн дээр **«Gemini жор»** эсвэл **«Gemini»** badge харагдана (mock биш).
4. Терминалд `[Gemini] generation failed` гэж гарвал сүлжээ / түлхүүр / JSON алдаа — энэ үед автоматаар mock руу шилжинэ.

## TheMealDB турших

1. **Тухай** хуудас руу орно.
2. «MealDB хайх» формд орцын жагсаалт бичнэ (жишээ: `төмс, өндөг`).
3. Эсвэл `http://127.0.0.1:5000/mealdb/random` — санамсаргүй жор.

Чөлөөт API нэг удаад **нэг орцоор** шүүдэг тул олон орцыг дараалан хайж, `idMeal`-ээр давхардыг хасна (`app.py` болон `MealDBService`).

## Төслийн бүтэц

```
moodmeal_ai/
  app.py
  config.py
  models.py
  seed.py
  requirements.txt
  .env.example
  README.md
  services/
  templates/
  static/
```

## Асуудал шийдвэрлэх

- **Импорт алдаа**: `venv` идэвхжүүлсэн эсэх, `pip install -r requirements.txt` дахин ажиллуулна.
- **Өгөгдөл байхгүй**: `python seed.py`.
- **MealDB хоосон**: сүлжээ, эсвэл орцын нэр англи хэл рүү зөв хөрвөөгүй байж магадгүй — `services/ingredient_mapper.py`-г өргөтгөнө.
- **Gemini JSON алдаа**: загвар буруу JSON өгвөл mock ашиглагдана — `.env` дээр `GEMINI_MODEL=gemini-2.5-flash` байгаа эсэхийг шалгана.

## Лиценз

Жишээ төсөл — өөрийн хэрэгцээнд өөрчилж ашиглана уу.
