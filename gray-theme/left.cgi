#!/usr/local/bin/perl
# Show the left-side menu of Virtualmin domains, plus modules
use strict;
use warnings;

# Globals
our %in;
our %text;
our $base_remote_user;
our %miniserv;
our %gaccess;
our $session_id;

our $trust_unknown_referers = 1;
require "gray-theme/gray-theme-lib.pl";
require "gray-theme/theme.pl";
ReadParse();

popup_header("Virtualmin");
print "<script type='text/javascript' src='@{[&get_webprefix()]}/unauthenticated/toggleview.js'></script>\n";

my $is_master;
# Is this user root?
if (foreign_available("virtual-server")) {
	foreign_require("virtual-server");
	$is_master = virtual_server::master_admin();
	}
elsif (foreign_available("server-manager")) {
	foreign_require("server-manager");
	$is_master = server_manager::can_action(undef, "global");
	}

# Find all left-side items from Webmin
my $sects = get_right_frame_sections();
my @leftitems = list_combined_webmin_menu($sects, \%in);
my @lefttitles = grep { $_->{'type'} eq 'title' } @leftitems;

# Work out what mode selector contains
my @has = ( );
my %modmenu;
foreach my $title (@lefttitles) {
	push(@has, { 'id' => $title->{'module'},
		     'desc' => $title->{'desc'},
		     'icon' => $title->{'icon'} });
	$modmenu{$title->{'module'}}++;
	}
my $nw = $sects->{'nowebmin'} || 0;
if ($nw == 0 || $nw == 2 && $is_master) {
	my $p = get_product_name();
	push(@has, { 'id' => 'modules',
		     'desc' => $text{'has_'.$p},
		     'icon' => '/images/'.$p.'-small.png' });
	}

# Default left-side mode
my $mode = $in{'mode'} ? $in{'mode'} :
	   $sects->{'tab'} =~ /vm2/ ? "server-manager" :
	   $sects->{'tab'} =~ /virtualmin/ ? "virtual-server" :
	   $sects->{'tab'} =~ /mail/ ? "mailboxes" :
	   @leftitems ? $has[0]->{'id'} : "modules";

# Show mode selector
if (indexof($mode, (map { $_->{'id'} } @has)) < 0) {
	$mode = $has[0]->{'id'};
	}
if (@has > 1) {
	print "<div class='mode'>";
	foreach my $m (@has) {
		print "<b>";
		if ($m->{'id'} ne $mode) {
			print "<a href='left.cgi?mode=$m->{'id'}'>";
			}
		if ($m->{'icon'}) {
			my $icon = add_webprefix($m->{'icon'});
			print "<img src='$icon' alt='$m->{'id'}'> ";
			}
		print $m->{'desc'};
		if ($m->{'id'} ne $mode) {
			print "</a>\n";
			}
		print "</b>\n";
		}
	print "</div>";
	}

print "<div class='wrapper'>\n";
print "<table id='main' width='100%'><tbody><tr><td>\n";

my $selwidth = (get_left_frame_width() - 70)."px";
if ($mode eq "modules") {
	# Only showing Webmin modules
	@leftitems = &list_modules_webmin_menu();
	foreach my $l (@leftitems) {
		$l->{'members'} = [ grep { !$modmenu{$_->{'id'}} } @{$l->{'members'}} ];
		}
	push(@leftitems, { 'type' => 'hr' });
	}
else {
	# Only show items under some title OR items that have no title
	my ($lefttitle) = grep { $_->{'id'} eq $mode } @lefttitles;
	my %titlemods = map { $_->{'module'}, $_ } @lefttitles;
	@leftitems = grep { $_->{'module'} eq $mode ||
			    !$titlemods{$_->{'module'}} } @leftitems;
	}

# Show system information link
push(@leftitems, { 'type' => 'item',
		   'id' => 'home',
		   'desc' => $text{'left_home'},
		   'link' => '/right.cgi',
		   'icon' => '/images/gohome.png' });

# Show refresh modules link
if ($mode eq "modules" && foreign_available("webmin")) {
	push(@leftitems, { 'type' => 'item',
			   'id' => 'refresh',
			   'desc' => $text{'main_refreshmods'},
			   'link' => '/webmin/refresh_modules.cgi',
			   'icon' => '/images/reload.png' });
	}

# Show logout link
get_miniserv_config(\%miniserv);
if ($miniserv{'logout'} && !$ENV{'SSL_USER'} && !$ENV{'LOCAL_USER'} &&
    $ENV{'HTTP_USER_AGENT'} !~ /webmin/i) {
	my $logout = { 'type' => 'item',
		       'id' => 'logout',
		       'target' => 'window',
		       'icon' => '/images/stock_quit.png' };
	if ($main::session_id) {
		$logout->{'desc'} = $text{'main_logout'};
		$logout->{'link'} = '/session_login.cgi?logout=1';
		}
	else {
		$logout->{'desc'} = $text{'main_switch'};
		$logout->{'link'} = '/switch_user.cgi';
		}
	push(@leftitems, $logout);
	}

# Show link back to original Webmin server
if ($ENV{'HTTP_WEBMIN_SERVERS'}) {
	push(@leftitems, { 'type' => 'item',
			  'desc' => $text{'header_servers'},
			  'link' => $ENV{'HTTP_WEBMIN_SERVERS'},
			  'icon' => '/images/webmin-small.gif',
			  'target' => 'window' });
	}

# Show Webmin search form
my $cansearch = ($gaccess{'webminsearch'} || '') ne '0' &&
		!$sects->{'nosearch'};
if ($mode eq "modules" && $cansearch) {
	push(@leftitems, { 'type' => 'input',
			   'desc' => $text{'left_search'},
			   'name' => 'search',
			   'cgi' => '/webmin_search.cgi', });
	}

show_menu_items_list(\@leftitems, 0);

print "</td></tr></tbody></table>\n";
print "</div>\n";
popup_footer();

# show_menu_items_list(&list, indent)
# Actually prints the HTML for menu items
sub show_menu_items_list
{
my ($items, $indent) = @_;
foreach my $item (@$items) {
	if ($item->{'type'} eq 'item') {
		# Link to some page
		my $it = $item->{'target'} || '';
		my $t = $it eq 'new' ? '_blank' :
			$it eq 'window' ? '_top' : 'right';
		my $link = add_webprefix($item->{'link'});
		if ($item->{'link'} =~ /^(https?):\/\//) {
			$t = '_blank';
			$link = $item->{'link'};
			}
		if ($item->{'icon'}) {
			my $icon = add_webprefix($item->{'icon'});
			print "<div class='linkwithicon".
			      ($item->{'inactive'} ? ' inactive' : '')."'>".
			      "<img src='$icon' alt=''>\n";
			}
		my $cls = $item->{'icon'} ? 'aftericon' :
		          $indent ? 'linkindented'.
		                    ($item->{'inactive'} ? ' inactive' : '').
		                    '' : 'leftlink';
		print "<div class='$cls'>";
		print "<a href='$link' target=$t>".
		      "$item->{'desc'}</a>";
		print "</div>";
		if ($item->{'icon'}) {
			print "</div>";
			}
		print "\n";
		}
	elsif ($item->{'type'} eq 'cat') {
		# Start of a new category
		my $c = $item->{'id'};
		print "<div class='linkwithicon'>";
		print "<a href=\"javascript:toggleview('cat$c','toggle$c')\" ".
		      "id='toggle$c'><img border='0' src='images/closed.gif' ".
		      "alt='[+]'></a>\n";
		print "<div class='aftericon'>".
		      "<a href=\"javascript:toggleview('cat$c','toggle$c')\" ".
		      "id='toggletext$c'>".
		      "<font color='#000000'>$item->{'desc'}</font></a></div>";
		print "</div>\n";
		print "<div class='itemhidden' id='cat$c'>\n";
		show_menu_items_list($item->{'members'}, $indent+1);
		print "</div>\n";
		}
	elsif ($item->{'type'} eq 'html') {
		# Some HTML block
		print "<div class='leftlink'>",$item->{'html'},"</div>\n";
		}
	elsif ($item->{'type'} eq 'text') {
		# A line of text
		print "<div class='leftlink'>",
		      html_escape($item->{'desc'}),"</div>\n";
		}
	elsif ($item->{'type'} eq 'hr') {
		# Separator line
		print "<hr>\n";
		}
	elsif ($item->{'type'} eq 'menu' || $item->{'type'} eq 'input') {
		# For with an input of some kind
		if ($item->{'cgi'}) {
			my $cgi = add_webprefix($item->{'cgi'});
			print "<form action='$cgi' target=right>\n";
			}
		else {
			print "<form>\n";
			}
		foreach my $h (@{$item->{'hidden'}}) {
			print ui_hidden(@$h);
			}
		print ui_hidden("mode", $mode);
		print "<div class='leftlink'>";
		print $item->{'desc'},"\n";
		if ($item->{'type'} eq 'menu') {
			my $sel = "";
			if ($item->{'onchange'}) {
				$sel = "window.parent.frames[1].location = ".
				       "\"$item->{'onchange'}\" + this.value";
				}
			print ui_select($item->{'name'}, $item->{'value'},
					 $item->{'menu'}, 1, 0, 0, 0,
					 "onChange='form.submit(); $sel' ".
					 "style='width:$selwidth'");
			}
		elsif ($item->{'type'} eq 'input') {
			print ui_textbox($item->{'name'}, $item->{'value'},
					  $item->{'size'});
			}
		if ($item->{'icon'}) {
			my $icon = add_webprefix($item->{'icon'});
			print "<input type=image src='$icon' ".
			      "border=0 class=goArrow>\n";
			}
		print "</div>";
		print "</form>\n";
		}
	elsif ($item->{'type'} eq 'title') {
		# Nothing to print here, as it is used for the tab title
		}
	}
}

# module_to_menu_item(&module)
# Converts a module to the hash ref format expected by show_menu_items_list
sub module_to_menu_item
{
my ($minfo) = @_;
return { 'type' => 'item',
	 'id' => $minfo->{'dir'},
	 'desc' => $minfo->{'desc'},
	 'link' => '/'.$minfo->{'dir'}.'/' };
}

# add_webprefix(link)
# If a URL starts with a / , add webprefix
sub add_webprefix
{
my ($link) = @_;
return $link =~ /^\// ? &get_webprefix().$link : $link;
}
