import importlib
names = ['anthropic','langgraph','fairlearn','weasyprint','pgvector','sentence_transformers']
for n in names:
    try:
        m = importlib.import_module(n)
        v = getattr(m, '__version__', None)
        print(f"{n}: imported, version={v}")
    except Exception as e:
        print(f"{n}: FAILED -> {e.__class__.__name__}: {e}")
print('done')
