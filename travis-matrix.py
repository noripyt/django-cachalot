#!/usr/bin/env python

from subprocess import check_output


envs = check_output(['tox', '-l'])

print('matrix:')
print('  include:')
for env in filter(bool, envs.decode().split('\n')):
    print('    - python: %s' % env[2:5])
    print('      env: TOXENV=' + env)
