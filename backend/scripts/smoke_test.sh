#!/usr/bin/env bash
set -e
BASE=${BASE:-http://localhost:8000}

echo "== health =="
curl -s $BASE/api/v1/health | python -m json.tool

echo "== generating sample image + mask =="
python -c "
from PIL import Image
import io
img = io.BytesIO(); Image.new('RGB', (100, 100), 'white').save(img, 'PNG')
m = io.BytesIO(); Image.new('L', (100, 100), 255).save(m, 'PNG')
open('/tmp/i.png', 'wb').write(img.getvalue())
open('/tmp/m.png', 'wb').write(m.getvalue())
"

echo "== submit task =="
TASK_ID=$(curl -s -X POST $BASE/api/v1/inpaint \
  -F "image=@/tmp/i.png" \
  -F "mask=@/tmp/m.png" | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "task_id=$TASK_ID"

sleep 2

echo "== poll =="
curl -s $BASE/api/v1/tasks/$TASK_ID | python -m json.tool

echo "== download =="
curl -s -o /tmp/r.png $BASE/api/v1/results/$TASK_ID.png
file /tmp/r.png
