use strict;
use warnings;
our %userconfig; # Export this

do 'mailbox-lib.pl';

# If addressbook whitelisting is enabled, update the whitelist
sub config_post_save
{
my ($config, $oldconfig, $canconfig) = @_;
%userconfig = %$config;
&addressbook_to_whitelist();
}
