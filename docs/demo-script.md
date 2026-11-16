# Demo Script

Recording guide for the 2–3 minute demo video.

**Before you start:** run `pip install -r requirements.txt`, then `python seed.py` to load the demo data (5 contacts, 2 favorites, 4 with multiple methods).

Suggested setup: 1440×900 or larger, browser zoom at 100%, recording with OBS or the built-in Windows recorder (`Win + G`).

---

## Pre-flight checklist (do not record this part)

1. Close unrelated windows; leave a single browser tab.
2. Confirm `data/address_book.db` holds the seed data.
3. Open a terminal in the project root.
4. Open a file explorer window at the project root so the exported `.xlsx` is easy to show.

---

## Storyboard

### Shot 1 — Start the server (~15 s)

| Action | Narration points |
| --- | --- |
| Run `python app.py` | "Flask listens on `0.0.0.0:5000`" |
| Show `* Running on http://127.0.0.1:5000` | "Starts cleanly on the first try, no errors" |

### Shot 2 — Open the list page (~10 s)

| Action | Narration points |
| --- | --- |
| Visit `http://127.0.0.1:5000/` | Card layout; favorited contacts show an accent bar on the left |
| Hover a card | Subtle lift and shadow transition on hover |

### Shot 3 — Search (~10 s)

| Action | Narration points |
| --- | --- |
| Type `福州` in the search box | 300 ms debounce filters automatically; only matching cards remain |
| Clear the box | The full list returns |

### Shot 4 — Create a contact with three method types (~40 s)

| Action | Narration points |
| --- | --- |
| Click **新增** | The drawer slides in from the right |
| Name `陈晓`, company `福州大学计算机学院`, note `同组做前端的同学，演示用` | Field walkthrough |
| Row 1: type 电话, value `13612345678` | |
| Click **+ 添加一条联系方式** | Rows are added dynamically |
| Row 2: type 邮箱, label `学校邮箱`, value `cx@fzu.edu.cn` | Demonstrates a custom label |
| Add a third row: type 微信, value `chenxiao_wx` | Three rows, three different types |
| Click **保存** | Drawer closes; the new card appears in the list |

### Shot 5 — Favorite and filter (~25 s)

| Action | Narration points |
| --- | --- |
| Click the star on the new card | Icon fills immediately, accent bar appears, toast confirms |
| Click **只看收藏** | Only favorited contacts are listed |
| **Reload the page (F5)** | "The state survives a reload, so it is stored in the database, not just in the front end" |
| Click **全部** | Full list returns |

### Shot 6 — Edit and delete (~25 s)

| Action | Narration points |
| --- | --- |
| Click **编辑** on a card | The drawer opens with every field and method row pre-filled |
| Change the note, add an 地址 row, save | The list updates immediately |
| Click **删除** on the demo contact | A confirmation dialog appears, naming the contact |
| Cancel once, then confirm | "Deleting requires a second confirmation, so it is hard to trigger by accident" |

### Shot 7 — Export to Excel (~20 s)

| Action | Narration points |
| --- | --- |
| Click **导出** | Browser downloads `contacts_YYYYMMDD.xlsx` |
| Open the file in Excel | One contact per row; the three phone/email columns for 张三 are filled separately |
| Point at the `是否收藏` column and the frozen, bold header | Walk through the Excel rules one by one |
| Point at a cell like `工作邮箱:zhangsan@example.com` | "Custom labels are preserved in a `label:value` form so a re-import restores them" |

### Shot 8 — Import failure (~25 s)

| Action | Narration points |
| --- | --- |
| Open the exported file, delete the `邮箱2` column, save as a new file | Deliberately break the header |
| Back in the app, click **导入** | The panel explains the three-step flow |
| Choose the broken file, click **开始导入** | Red panel: "表头不符合模板，请下载模板后填写" |

### Shot 9 — Import success (~25 s)

| Action | Narration points |
| --- | --- |
| Click **下载模板** | Get the blank template |
| Fill in 2–3 rows, leaving one name blank | "A blank name is skipped, not silently dropped" |
| Import that file | Yellow panel: "成功新增 2 条，跳过 1 条" with "第4行：姓名不能为空" |

### Shot 10 — Responsive layout (~15 s)

| Action | Narration points |
| --- | --- |
| Open DevTools device toolbar | |
| Resize to ~900 px | Three columns become two |
| Resize below 600 px | Single column; the drawer fills the screen |

### Shot 11 — Wrap up (~10 s)

| Action | Narration points |
| --- | --- |
| Back in the terminal, press `Ctrl + C` | "Deployed locally, import and export round-trip losslessly" |

---

## Screenshots

All eight screenshots below are already captured from the running application and live in [`screenshots/`](screenshots/):

| File | Content |
| --- | --- |
| `01-list.png` | Contact list with favorite accent bars and method summaries |
| `02-create-drawer.png` | Create drawer with three methods across three types |
| `03-favorites.png` | "Favorites only" filter |
| `04-edit-drawer.png` | Edit drawer with pre-filled data |
| `05-excel-export.png` | Exported workbook opened in Excel |
| `06-import-error.png` | Import rejected because the header was modified |
| `07-import-success.png` | Import result: 2 inserted, 1 skipped, with error detail |
| `08-responsive.png` | Two-column responsive layout at 900 px |

To regenerate them, run the app with the seed data loaded, then repeat the steps above and capture the screen. The names above are what the README links to, so keep them if you replace a file.

---

## Recording tips

- Record at 1080p or above; the card grid looks cramped below 720p.
- Keep the mouse movements deliberate — the hover transitions are part of the style score.
- Say the field names out loud as you fill them; the graders follow the API contract, and naming the fields makes the mapping obvious.
- Do not cut the F5 reload in Shot 5 — it is the proof that favorites are persisted rather than held in memory.
