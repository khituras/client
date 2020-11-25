import os
import wandb
import numpy as np
import argparse
import time
import shutil

APPROX_MB_PER_ROW = 0.295

def build_table(n_rows):
    return wandb.Table(
        columns=["id", "image"],
        data=[
            [i, wandb.Image(np.random.randint(0, 255, size=(320,320,3)))]
            for i in range(n_rows)
        ]
    )

def safe_remove_dir(dir_name):
    if dir_name not in [".", "~", "/"] and os.path.exists(dir_name):
        shutil.rmtree(dir_name)

def delete_cache():
    safe_remove_dir("./artifacts")
    safe_remove_dir("~/.cache/wandb")

def cleanup():
    delete_cache()
    safe_remove_dir("./wandb")


def main(n_rows, clear_cache):
    timer = {
        "LOG_TABLE": [None, None],
        "GET_TABLE": [None, None],
        "LOG_REF": [None, None],
        "GET_REF": [None, None],
    }
    delete_cache()
    with wandb.init() as run:
        table = build_table(n_rows)
        artifact = wandb.Artifact("table_load_test", "table_load_test")
        artifact.add(table, "table")
        timer["LOG_TABLE"][0] = time.time()
        run.log_artifact(artifact)
    timer["LOG_TABLE"][1] = time.time()

    if clear_cache: delete_cache()
    with wandb.init() as run:
        artifact = run.use_artifact("table_load_test:latest")
        timer["GET_TABLE"][0] = time.time()
        table = artifact.get("table")
        timer["GET_TABLE"][1] = time.time()
        artifact = wandb.Artifact("table_load_test_ref", "table_load_test")
        artifact.add(table, "table_ref")
        timer["LOG_REF"][0] = time.time()
        run.log_artifact(artifact)
    timer["LOG_REF"][1] = time.time()
    
    if clear_cache: delete_cache()
    with wandb.init() as run:
        artifact = run.use_artifact("table_load_test_ref:latest")
        timer["GET_REF"][0] = time.time()
        table = artifact.get("table")
        timer["GET_REF"][1] = time.time()

    print("Version\tRows\tBytes\tCleared\tLOG_TAB\tGET_TAB\tLOG_REF\tGET_REF\t")
    print("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t".format(
        wandb.__version__,
        n_rows,
        round(n_rows * APPROX_MB_PER_ROW, 3),
        clear_cache,
        round(timer["LOG_TABLE"][1] - timer["LOG_TABLE"][0], 3),
        round(timer["GET_TABLE"][1] - timer["GET_TABLE"][0], 3),
        round(timer["LOG_REF"][1] - timer["LOG_REF"][0], 3),
        round(timer["GET_REF"][1] - timer["GET_REF"][0], 3),
    ))
    
    cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_rows', type=int, default=1000, help='foo help')
    parser.add_argument('--clear_cache', type=bool, default=True, help='foo help')
    args = vars(parser.parse_args())
    main(**args)