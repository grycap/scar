#!/bin/bash
# Configure HTCondor and fire up supervisord
# Daemons for each role
MASTER_DAEMONS="COLLECTOR, NEGOTIATOR"
EXECUTOR_DAEMONS="STARTD"
SUBMITTER_DAEMONS="SCHEDD"

usage() {
  cat <<-EOF
	usage: $0 -m|-e master-address|-s master-address [-c url-to-config] [-k url-to-public-key] [-u inject user -p password] [-C Condor Connection Broker (CCB) -P Private Network Namei -S Shared Secret]
	
	Configure HTCondor role and start supervisord for this container. 
	
	OPTIONS:
	  -m                	configure container as HTCondor master
	  -e master-address 	configure container as HTCondor executor for the given master
	  -s master-address 	configure container as HTCondor submitter for the given master
	  -c url-to-config  	config file reference from http url.
	  -k url-to-public-key	url to public key for ssh access to root
	  -u inject user	inject a user without root privileges for submitting jobs accessing via ssh. -p password required
	  -p password		user password (see -u attribute).
	  -C ccb		Condor Connection Broker (CCB).
	  -P private network	Private Network Name parameter for condor_config.
	  -S shared secret	Shared secret.
	EOF
  exit 1
}

# Syntax checks
CONFIG_MODE=
SSH_ACCESS=

# Get our options
ROLE_DAEMONS=
CONDOR_HOST=
HEALTH_CHECKS=
CONFIG_URL=
KEY_URL=
USER=
PASSWORD=
CCB=
PRIVATE_NETWORK_NAME=
SHARED_SECRET=
while getopts ':me:s:c:k:u:p:C:P:S:' OPTION; do
  case $OPTION in
    m)
      [ -n "$ROLE_DAEMONS" ] && usage
      ROLE_DAEMONS="$MASTER_DAEMONS"
      CONDOR_HOST='$(FULL_HOSTNAME)'
      HEALTH_CHECK='master'
    ;;
    e)
      [ -n "$ROLE_DAEMONS" -o -z "$OPTARG" ] && usage
      ROLE_DAEMONS="$EXECUTOR_DAEMONS"
      CONDOR_HOST="$OPTARG"
      HEALTH_CHECK='executor'
    ;;
    c)
      [ -n "$CONFIG_MODE" -o -z "$OPTARG" ] && usage
      CONFIG_MODE='http'
      CONFIG_URL="$OPTARG"
    ;;
    s)
      [ -n "$ROLE_DAEMONS" -o -z "$OPTARG" ] && usage
      ROLE_DAEMONS="$SUBMITTER_DAEMONS"
      CONDOR_HOST="$OPTARG"
      HEALTH_CHECK='submitter'
    ;;
    k)
      [ -n "$KEY_URL" -o -z "$OPTARG" ] && usage
      SSH_ACCESS='yes'
      KEY_URL="$OPTARG"
    ;;  
    u)
      [ -n "$USER" -o -z "$OPTARG" ] && usage
      SSH_ACCESS='yes'
      USER="$OPTARG"
    ;;  
    p)
      [ -n "$PASSWORD" -o -z "$OPTARG" ] && usage
      SSH_ACCESS='yes'
      PASSWORD="$OPTARG"
    ;;  
    C)
      [ -n "$CCB" -o -z "$OPTARG" ] && usage
      CCB="$OPTARG"
    ;;   
    P)
      [ -n "$PRIVATE_NETWORK_NAME" -o -z "$OPTARG" ] && usage
      PRIVATE_NETWORK_NAME="$OPTARG"
    ;; 
    S)
      [ -n "$SHARED_SECRET" -o -z "$OPTARG" ] && usage
      SHARED_SECRET="$OPTARG"
    ;;  
    *)
      usage
    ;;
  esac
done

# Additional checks
# USER XOR PASSWORD
if [ \( -n "$PASSWORD" -a -z "$USER" \) -a \( -z "$PASSWORD" -a -n "$USER" \) ]; then
  usage
fi;
# CCB and Private Network Name must be declared none or together
if [ \( -n "$CCB" -a -z "$PRIVATE_NETWORK_NAME" \) -a \( -z "$CCB" -a -n "$PRIVATE_NETWORK_NAME" \) ]; then
  usage
fi;

# Prepare SSH access
if [ -n "$KEY_URL" -a -n "$SSH_ACCESS" ]; then
  wget -O - "$KEY_URL" > /root/.ssh/authorized_keys
fi

if [ -n "$USER" -a -n "$PASSWORD" -a -n "$SSH_ACCESS" ]; then
  mkdir /home/$USER && useradd $USER -d /home/$USER -s /bin/bash && echo "$USER:$PASSWORD" | chpasswd && chown -R $USER. /home/$USER/
fi;

if [ -n "$SSH_ACCESS" ]; then

  cat >> /etc/supervisor/conf.d/supervisord.conf << EOL
[program:sshd]
command=/usr/sbin/sshd -D
autostart=true
stdout_logfile=/var/log/ssh/sshd.stdout.log
stdout_logfile_maxbytes=1MB
stdout_logfile_backups=10
stderr_logfile=/var/log/ssh/sshd.stderr.log
stderr_logfile_maxbytes=1MB
stderr_logfile_backups=10
EOL

fi;

# Prepare external config
if [ -n "$CONFIG_MODE" ]; then
  wget -O - "$CONFIG_URL" > /etc/condor/condor_config
fi

# Prepare HTCondor configuration
sed -i \
  -e 's/@CONDOR_HOST@/'"$CONDOR_HOST"'/' \
  -e 's/@ROLE_DAEMONS@/'"$ROLE_DAEMONS"'/' \
  /etc/condor/condor_config

# Prepare right HTCondor healthchecks
sed -i \
  -e 's/@ROLE@/'"$HEALTH_CHECK"'/' \
  /etc/supervisor/conf.d/supervisord.conf

# Prepare HTCondor to CCB connection
if [ -n "$CCB" -a -n "$PRIVATE_NETWORK_NAME" -a -n "$SHARED_SECRET" ]; then
  cat >> /etc/condor/condor_config << _EOF_
CCB_ADDRESS = $CCB
PRIVATE_NETWORK_NAME = $PRIVATE_NETWORK_NAME
SEC_PASSWORD_FILE= /etc/condor/condorSharedSecret
SEC_DAEMON_INTEGRITY= REQUIRED
SEC_DAEMON_AUTHENTICATION= REQUIRED
SEC_DAEMON_AUTHENTICATION_METHODS= PASSWORD
SEC_CLIENT_AUTHENTICATION_METHODS= FS, PASSWORD
_EOF_

  condor_store_cred -f /etc/condor/condorSharedSecret -p $SHARED_SECRET
fi

exec /usr/local/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
