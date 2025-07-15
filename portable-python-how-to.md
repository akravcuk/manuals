
## Create folders
```bash
mkdir -p ~/python-portable/{rpms,tgz,extracted} && cd ~/python-portable/rpms
```

## Download RPMs (still needed)
```bash
dnf download --resolve --alldeps python3 python3-libs python3-pip
```

## Convert RPMs into .tar.gz
```bash
for rpm in *.rpm; do rpm2archive "$rpm"; done
```

## Extract and install
```bash
sudo mkdir -p /opt/python

# 1
platform-python-3.6.8-69.el8_10.alma.1.x86_64.rpm.tgz -> /opt/python

python3-libs-3.6.8-69.el8_10.alma.1.x86_64.rpm.tgz -> /opt/python/lib64

# 2
ln -s /opt/python/python-<smth> ./python

# extract python libs too -> /opt/python/lib64
```

## create a file `.python-env.sh` in home directory
```
export PYTHONHOME=/opt/python
export LD_LIBRARY_PATH=/opt/python/lib64
export PATH=/opt/python:$PATH
```

## add to ~./bashrc
```bash
if [ -f "$HOME/.python-env.sh" ]; then
    source "$HOME/.python-env.sh"
fi
```

## test
```bash
source ./.python-env.sh

# must work
python
```



# In case if you have old CentOS 6
1. create repo file
```
 cat ./centos-sclo-rh.repo
[centos-sclo-rh]
name=CentOS-6 - SCLo rh
baseurl=http://vault.centos.org/6.10/sclo/x86_64/rh/
enabled=1
gpgcheck=0
```

2. download
```
sudo yum install --downloadonly \
  --downloaddir=./python-rpms \
  --setopt=tsflags=nocontexts,noscripts,nodocs,noreplace \
  rh-python36 rh-python36-python rh-python36-python-libs
```

3. rest is the same
