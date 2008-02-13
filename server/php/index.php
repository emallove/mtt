<?php

#
# Copyright (c) 2006 Sun Microsystems, Inc.
#                         All rights reserved.
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
#

$topdir = ".";
if (file_exists("$topdir/config.inc")) {
    include_once("$topdir/config.inc");
}

#
#
# Web-based Open MPI Tests Querying Tool
#
#
$global_sql_time_elapsed = 0;

# Set PHP trace levels
if (isset($_GET['verbose']) or 
    isset($_GET['debug']))
    error_reporting(E_ALL);
else
    error_reporting(E_ERROR | E_PARSE);

# Includes
$topdir = ".";
include_once("$topdir/reporter.inc");
include_once("$topdir/screen.inc");
include_once("$topdir/report.inc");
include_once("$topdir/database.inc");

# 'debug' is an aggregate trace
if (isset($_GET['debug'])) {
    $_GET['verbose'] = 'on';
    $_GET['dev']     = 'on';
    $_GET['cgi']     = 'on';
}

# 'stats' and 'explain' would not make sense without 'sql'
if (isset($_GET['stats']) or 
    isset($_GET['explain']) or 
    isset($_GET['analyze'])) {
    $_GET['sql'] = '2';
}

# In case we're using this script from the command-line
if ($argv)
    $_GET = getoptions($argv);

# Create or redirect to a permalink
$do_redir = $_GET['do_redir'];
$make_redir = $_GET['make_redir'];
if (! is_null($do_redir))
    do_redir($do_redir);
elseif (! is_null($make_redir))
    make_redir($_GET);

#
# Increase the memory limit for PHP so it can handle larger queries.
# This is a work around for bug #62
#
ini_set("memory_limit","32M");

# Keep track of time
$start = time();

# Display a query screen and report
dump_report();

# Report on script's execution time
$finish = time();
$elapsed = $finish - $start;
print("\n<br><p>Total script execution time: " . $elapsed . " second(s)");
print("\n<br><p>Total SQL execution time: " . $global_sql_time_elapsed . " second(s)</p>");

# Display input parameters
debug_cgi($_GET, "GET " . __LINE__);

# Display cookie parameters
debug_cgi($_COOKIE, "COOKIE " . __LINE__);

print hidden_carryover($_GET) .
      "\n<hr></form>$mtt_body_html_suffix</body></html>";

exit;

# Create a tiny URL permalink (using the current URL), and exit
function make_redir($params) {

    unset($params["make_redir"]);
    unset($params["do_redir"]);

    $qstring = arr2qstring($params);

    $domain = $_SERVER['SERVER_NAME'];
    $script = $_SERVER['SCRIPT_NAME'];
    $url    = "http://$domain$script?$qstring";

    # Create tiny URLs for the permalinks
    $query = "SELECT permalink_id FROM permalinks WHERE permalink = '$url'";
    $id = select_scalar($query);

    if (is_null($id)) {
        $query = "SELECT nextval('permalinks_permalink_id_seq')";
        $id = select_scalar($query);
        $insert = 
            "INSERT INTO " .
                "permalinks (permalink_id, permalink) " . 
                "VALUES ('$id', '$url');";
        do_pg_query($insert);
    }

    $tinyurl = "http://$domain$script?do_redir=$id";

    # Print tiny link in a tiny window
    $t = 50;
    print "<html>\n" . html_head("Tiny link") .
"<body>
<div align=center>
<p>The original permalink was " . strlen($url) . " chars long.
Here's a tiny link that is only $t chars long:</p>

<p><form name=url_form><code>
<input type=text name=url value='$tinyurl' size=$t
    onFocus=\"this.value='$tinyurl';\" readonly>
</code>
</form></p>

<script language='javascript' type='text/javascript'>
document.url_form.url.focus();
document.url_form.url.select();
</script>

<p><form>
<input type=button value='Close this window' onClick='javascript:window.close();'>
</form></p>

</div>
</body>
</html>";
    exit;
}

# Redirect the browser to the permalink shortcut
function do_redir($id) {
    $query = "SELECT permalink FROM permalinks WHERE permalink_id = '$id'";
    $url = select_scalar($query);
    header("Location: $url");
    exit;
}

?>
