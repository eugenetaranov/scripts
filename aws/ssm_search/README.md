```bash
usage: ssm_search.py [-h] [--cache CACHE] [--parameter PARAMETER] [--list] [--reset] [--search [SEARCH ...]]

options:
  -h, --help            show this help message and exit
  --cache CACHE         Cache path
  --parameter PARAMETER
                        Parameter name
  --list                List all parameters
  --reset               Reset cache
  --search [SEARCH ...]
                        Search keywords
```

### Installation
```bash
sudo curl -fsSL https://raw.githubusercontent.com/eugenetaranov/scripts/refs/heads/master/aws/ssm_search/ssm_search.py -o /usr/local/bin/ssm_search
sudo chmod +x /usr/local/bin/ssm_search
```
