cp2dir="/data/03261/polonius/image_db_staging/"
db_dir="./"
imgdir="all_pngs"
rpt="elixer_reports_"
nei="_nei"
mini="_mini"

echo Running prefixes 0 to 12
echo This copies databases to staging location.

read -p "Press enter to continue"

for i in {20000..20012}
do
  echo "$db_dir$rpt$i.db"
  
  python3 make_report_db.py --db_name "$db_dir$rpt$i.db" --img_dir $imgdir --img_name "$i*[0-9].png" --mv2dir $cp2dir &
  
  python3 make_report_db.py --db_name "$db_dir$rpt$i$nei.db" --img_dir  $imgdir  --img_name "$i*[0-9]nei.png" --mv2dir $cp2dir &
  
  python3 make_report_db.py --db_name "$db_dir$rpt$i$mini.db" --img_dir  $imgdir  --img_name "$i*[0-9]mini.png" --mv2dir $cp2dir &

done