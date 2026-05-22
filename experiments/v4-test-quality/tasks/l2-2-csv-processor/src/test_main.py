import sys, os, tempfile; sys.path.insert(0, os.path.dirname(__file__))
from main import read_csv, filter_rows, aggregate, write_csv, process_pipeline

def test_read_csv():
    data = read_csv("nonexistent.csv")
    assert data == []
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="")
    tmp.write("name,score\nAlice,90\nBob,85\n")
    tmp.close()
    data = read_csv(tmp.name)
    assert len(data) == 2
    assert data[0]["name"] == "Alice"
    assert data[0]["score"] == "90"
    os.unlink(tmp.name)

def test_filter_rows():
    data = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}]
    assert len(filter_rows(data, {"name": "Alice"})) == 1
    assert len(filter_rows(data, {"name": "X"})) == 0
    assert len(filter_rows(data, {"name": "Alice", "score": "90"})) == 1
    assert len(filter_rows(data, {"name": "Alice", "score": "85"})) == 0
    assert len(filter_rows([], {"a": "1"})) == 0

def test_aggregate():
    data = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}, {"name": "Alice", "score": "60"}]
    result = aggregate(data, "name", {"op": "sum", "column": "score"})
    assert len(result) == 2
    for r in result:
        if r["name"] == "Alice":
            assert r["sum"] == 150.0
        elif r["name"] == "Bob":
            assert r["sum"] == 85.0
    count_result = aggregate(data, "name", {"op": "count", "column": "score"})
    assert len(count_result) == 2
    avg_result = aggregate(data, "name", {"op": "avg", "column": "score"})
    for r in avg_result:
        if r["name"] == "Alice":
            assert r["avg"] == 75.0
    min_result = aggregate(data, "name", {"op": "min", "column": "score"})
    max_result = aggregate(data, "name", {"op": "max", "column": "score"})
    assert aggregate([], "x", {"op": "sum"}) == []

def test_write_csv():
    data = [{"name": "Alice", "score": "90"}]
    outdir = tempfile.mkdtemp()
    outpath = os.path.join(outdir, "sub", "out.csv")
    write_csv(data, outpath)
    assert os.path.exists(outpath)
    read_back = read_csv(outpath)
    assert read_back[0]["name"] == "Alice"
    shutil.rmtree(outdir)

def test_process_pipeline():
    indir = tempfile.mkdtemp()
    outdir = tempfile.mkdtemp()
    inpath = os.path.join(indir, "in.csv")
    outpath = os.path.join(outdir, "out.csv")
    write_csv([{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}, {"name": "Alice", "score": "60"}], inpath)
    process_pipeline(inpath, outpath, {}, "name", "score", "sum")
    result = read_csv(outpath)
    assert len(result) == 2
    shutil.rmtree(indir)
    shutil.rmtree(outdir)
