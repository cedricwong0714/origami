# Host the live sandbox for a month (no Cursor agent)

This cloud VM and the trycloudflare link die when the agent stops. I cannot
leave a process running here. A free host that **you** own will stay up.

`origami` is **not** on PyPI. A host that runs `pip install origami` will
print "package not found". Install from this repo with `requirements.txt`
and start **`host_app.py`**, not `app.py`.

## Fastest free option: Streamlit Community Cloud (~always-on)

1. The public tree is already on GitHub:
   https://github.com/cedricwong0714/origami
2. Open [https://share.streamlit.io](https://share.streamlit.io) and sign in
   with GitHub.
3. **New app** → `cedricwong0714/origami` → branch `main` → **Main file path: `host_app.py`**.
4. Deploy. The HTTPS URL they give you stays up while the GitHub repo and
   the Streamlit app exist (months on the free tier). Idle apps may sleep
   and take a minute to wake.

## Same app on Hugging Face Spaces (also free, months)

1. Create a Space: SDK **Streamlit**, file **`host_app.py`**.
2. Push this repository into that Space, or upload the tree.
3. Space README can use `deploy/huggingface/README.md`.

## Docker (Render / Railway / a school VM)

```bash
docker build -t origami-sandbox .
docker run -p 8501:8501 origami-sandbox
```

`render.yaml` is a free Render web service. Free instances sleep when idle
but the service remains for more than a month.

## What stays local-only

The Cloudflare Quick Tunnel from the agent is gone when this session ends.
Vercel cannot execute Streamlit or numpy. It can serve `web/modelling-static/`
(a saved lookup of the live chassis). Deploy:

```bash
python scripts/write_modelling_static.py
npx vercel --cwd web/modelling-static --yes
```
