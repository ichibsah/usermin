#!/usr/local/bin/perl
# link.cgi
# Forward the URL from path_info on to another webmin server

require './tunnel-lib.pl';
$ENV{'PATH_INFO'} =~ /^\/(.*)$/ ||
	&error("Bad PATH_INFO : $ENV{'PATH_INFO'}");
$path = $1;
#$path = $1 ? &urlize("$1") : '/';
#$path =~ s/^%2F/\//;
if ($ENV{'QUERY_STRING'}) {
	$path .= '?'.$ENV{'QUERY_STRING'};
	}
elsif (@ARGV) {
	$path .= '?'.join('+', @ARGV);
	}
$url = "/$module_name/link.cgi";
$| = 1;
$meth = $ENV{'REQUEST_METHOD'};

if ($config{'loginmode'} == 2) {
	# Login is variable .. check if we have it yet
	if ($ENV{'HTTP_COOKIE'} =~ /tunnel=([^\s;]+)/) {
		# Yes - set the login and password to use
		($user, $pass) = split(/:/, &decode_base64("$1"));
		}
	else {
		# No - need to display a login form
		&ui_print_header(undef, $text{'login_title'}, "");

		print "<center>",&text('login_desc', "<tt>$config{'url'}</tt>"),
		      "</center><p>\n";
		print "<form action=/$module_name/login.cgi method=post>\n";
		print "<input type=hidden name=path value='",
			&html_escape($path),"'>\n";
		print "<center><table border>\n";
		print "<tr $tb> <td><b>$text{'login_header'}</b></td> </tr>\n";
		print "<tr $cb> <td><table cellpadding=2>\n";
		print "<tr> <td><b>$text{'login_user'}</b></td>\n";
		print "<td><input name=user size=20></td> </tr>\n";
		print "<tr> <td><b>$text{'login_pass'}</b></td>\n";
		print "<td><input name=pass size=20 type=password></td>\n";
		print "</tr> </table></td></tr></table>\n";
		print "<input type=submit value='$text{'login_login'}'>\n";
		print "<input type=reset value='$text{'login_clear'}'>\n";
		print "</center></form>\n";

		&ui_print_footer("", $text{'index_return'});
		exit;
		}
	}
elsif ($config{'loginmode'} == 1) {
	# Login is fixed
	$user = $config{'user'};
	$pass = $config{'pass'};
	}

# Connect to the server
($host, $port, $page, $ssl) = &parse_http_url($config{'url'});
$page .= "/" if ($page !~ /\/$/);
$host || &error(&text('link_eurl', $config{'url'}));
$path = $path eq "/" ? $page : $page.$path;
#&error("$host $port $ssl $meth $path");
$con = &make_http_connection($host, $port, $ssl, $meth, $path);
&error($con) if (!ref($con));

# Send request headers
&write_http_connection($con, "Host: $host\r\n");
&write_http_connection($con, "User-agent: Webmin\r\n");
if ($user) {
	$auth = &encode_base64("$user:$pass");
	$auth =~ s/\n//g;
	&write_http_connection($con, "Authorization: basic $auth\r\n");
	}
&write_http_connection($con, sprintf(
			"Webmin-servers: %s://%s:%d/$module_name/\n",
			$ENV{'HTTPS'} eq "ON" ? "https" : "http",
			$ENV{'SERVER_NAME'}, $ENV{'SERVER_PORT'}));
$cl = $ENV{'CONTENT_LENGTH'};
&write_http_connection($con, "Content-length: $cl\r\n") if ($cl);
&write_http_connection($con, "Content-type: $ENV{'CONTENT_TYPE'}\r\n")
	if ($ENV{'CONTENT_TYPE'});
&write_http_connection($con, "\r\n");
if ($cl) {
	read(STDIN, $post, $cl);
	&write_http_connection($con, $post);
	}

# read back the headers
$dummy = &read_http_connection($con);
while(1) {
	($headline = &read_http_connection($con)) =~ s/\r|\n//g;
	last if (!$headline);
	$headline =~ /^(\S+):\s+(.*)$/ || &error("Bad header");
	$header{lc($1)} = $2;
	$headers .= $headline."\n";
	}

$defport = $ssl ? 443 : 80;
if ($header{'location'} =~ /^(http|https):\/\/$host:$port$page(.*)$/ ||
    $header{'location'} =~ /^(http|https):\/\/$host$page(.*)/ &&
    $port == $defport) {
	# fix a redirect
	&redirect("$url/$2");
	exit;
	}
elsif ($header{'www-authenticate'}) {
	# Invalid login
	if ($config{'loginmode'} == 2) {
		print "Set-Cookie: tunnel=; path=/\n";
		&error(&text('link_eautologin', "<tt>$config{'url'}</tt>",
		     "/$module_name/link.cgi/$path"));
		}
	elsif ($user) {
		&error(&text('link_elogin', $host, $user));
		}
	else {
		&error(&text('link_enouser', $host));
		}
	}
else {
	# just output the headers
	print $headers,"\n";
	}

# read back the rest of the page
if ($header{'content-type'} =~ /text\/html/ && !$header{'x-no-links'}) {
	while($_ = &read_http_connection($con)) {
		s/src='$page([^']*)'/src='$url\/$1'/gi;
		s/src="$page([^"]*)"/src="$url\/$1"/gi;
		s/src=$page([^ "'>]*)/src=$url\/$1/gi;
		s/href='$page([^']*)'/href='$url\/$1'/gi;
		s/href="$page([^"]*)"/href="$url\/$1"/gi;
		s/href=$page([^ >"']*)/href=$url\/$1/gi;
		s/action='$page([^']*)'/action='$url\/$1'/gi;
		s/action="$page([^"]*)"/action="$url\/$1"/gi;
		s/action=$page([^ "'>]*)/action=$url\/$1/gi;
		s/\.location\s*=\s*'$page([^']*)'/.location='$url\/$1'/gi;
		s/\.location\s*=\s*"$page([^']*)"/.location="$url\/$1"/gi;
		s/window.open\("$page([^"]*)"/window.open\("$url\/$1"/gi;
		s/name=return\s+value="$page([^"]*)"/name=return value="$url\/$1"/gi;
		print;
		}
	}
else {
	while($buf = &read_http_connection($con, 1024)) {
		print $buf;
		}
	}
&close_http_connection($con);

