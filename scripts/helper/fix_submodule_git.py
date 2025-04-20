"""
Used to fix editable libraries not being properly initialized
as submodules
"""
import sys
import os
import subprocess
import functools


def run_subprocess(cmd: list[str]) -> str:
    """
    Runs a process

    Returns
    =======
    str
        The process output

    Raises
    ======
    subprocess.CalledProcessError
        If the process fails
    """
    result = subprocess.run(cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text   = True,
        check  = True
    )

    return result.stdout


@functools.lru_cache(1)
def get_repo_url(repo_path: str) -> str:
    """
    Gets URL of repo from given path

    Parameters
    ==========
    repo_path : str
        The path to the repo

    Returns
    =======
    str
        The repo URL

    Raises
    ======
    subprocess.CalledProcessError
        If the command fails
    """
    try: return run_subprocess([ f'{git}', '-C', repo_path, 'remote', 'get-url', 'origin' ]).strip()
    except subprocess.CalledProcessError as e:
        print(f'Failed to get repo URL for "{repo_path}"')
        print(f'Err: {e.cmd} returned {e.returncode}; {e.stderr}')
        raise


def check_submodule(repo_path: str):
    """
    Adds submodule to git index if not already added

    Parameters
    ==========
    repo_path : str
        The path to the repo

    Raises
    ======
    subprocess.CalledProcessError
        If the command fails
    """
    for _ in range(2):
        try: output = run_subprocess([ f'{git}', 'submodule', 'status', repo_path ])
        except subprocess.CalledProcessError as e:
            submodule_url  = get_repo_url(repo_path)
            submodule_path = repo_path.replace('\\', '/')

            print(f'Adding submodule {submodule_path} url ({submodule_url})...')
            run_subprocess([ f'{git}', 'submodule', 'add', '-f',submodule_url, submodule_path ])
            continue

        print(' ', output := output.strip())


if __name__ == '__main__':
    if 'VIRTUAL_ENV' not in os.environ:
        raise Exception('No virtual environment active')

    git       = os.environ.get('GIT', 'git')
    venv_path = os.path.relpath(os.environ['VIRTUAL_ENV'], os.getcwd())
    ret_ok    = True

    editable_path = f'{venv_path}{os.sep}src'

    for subdir in os.listdir(editable_path):
        repo_path = f'{editable_path}{os.sep}{subdir}'
        print(f'Checking repo path {repo_path}')

        try: check_submodule(repo_path)
        except subprocess.CalledProcessError as e:
            print(f'{e.cmd} returned {e.returncode}: {e.stderr}')
            ret_ok = False

        print(f'Updating submodule {repo_path}')

        try: output = run_subprocess([ f'{git}', 'submodule', 'init', repo_path ])
        except subprocess.CalledProcessError as e:
            print(f'{e.cmd} returned {e.returncode}: {e.stderr}')
            sys.exit(1)

        if output:
            print(output)

        try: output = run_subprocess([ f'{git}', 'submodule', 'update', repo_path ])
        except subprocess.CalledProcessError as e:
            print(f'{e.cmd} returned {e.returncode}: {e.stderr}')
            sys.exit(1)

        if output:
            print(output)

    sys.exit(0 if ret_ok else 1)
