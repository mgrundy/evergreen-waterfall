##waterfall.py##
**a command line Evergreen waterfall.**


*Created during MongoDB SkunkWorks some time in 2017*


waterfall.py uses your .evergreen.yml for things like server addresses. default project names and authentication. It should work with a local Evergreen installation. It uses the rest api exclusively (Max, I finally understand what you meant).


###Here are some examples:###


- Default mode (only show variants that have failures, uses your evergreen config):
~~~~
python waterfall.py
~~~~
- Default mode without an evergreen config, specify project (looks at mongo's evergreen)
~~~~
python waterfall.py -p mongodb-mongo-master
~~~~
- Summary mode (Summarize all variants, default (global) is three commits)
~~~~
python waterfall.py -p mongodb-mongo-master -s
~~~~
- We'll cut it down to just the first commit (-n 1) and add failure details (-d):
~~~~
python waterfall.py -p mongodb-mongo-master -n 1 -d
~~~~
- Let's add the links to the logs (-l)  so we can take a look:
~~~~
python waterfall.py -p mongodb-mongo-master -n 1 -d -l
~~~~
- System errors and timeouts will link to the task (when -l is used). System errors show magenta. Also, -n 0 will show the max number of commits (10)
~~~~
python waterfall.py -p mongodb-mongo-master -n 0 -d
~~~~
- To specify a different project use -p. This example is a private project, so it uses the user name and api key in your evergreen config file
~~~~
'python waterfall.py -s -p sqlproxy
~~~~
- You can also have it show all the build variants, regardless of failures (-a)
~~~~
python waterfall.py -p mongodb-mongo-master -n 1 -a
~~~~


That's pretty much it! Hope it's useful!
