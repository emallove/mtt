#!/usr/bin/env perl
#
# Copyright (c) 2005-2006 The Trustees of Indiana University.
#                         All rights reserved.
# Copyright (c) 2006-2007 Cisco Systems, Inc.  All rights reserved.
# $COPYRIGHT$
# 
# Additional copyrights may follow
# 
# $HEADER$
#

package MTT::Test::RunEngine;

use strict;
use File::Basename;
use Time::Local;
use MTT::Messages;
use MTT::Values;
use MTT::Reporter;
use MTT::Defaults;
use Data::Dumper;

#--------------------------------------------------------------------------

my $verbose_out;

#--------------------------------------------------------------------------

sub RunEngine {
    my ($section, $install_dir, $runs_data_dir, $mpi_details, $test_build, $force, $ret) = @_;
    my $test_results;
    my $total = $#{$ret->{tests}} + 1;

    # Loop through all the tests
    Verbose("   Total of $total tests to run in this section\n");
    $verbose_out = 0;
    my $count = 0;
    my $printed = 0;
    foreach my $run (@{$ret->{tests}}) {
        $printed = 0;
        if (!exists($run->{executable})) {
            Warning("No executable specified for text; skipped\n");
            next;
        }

        # Get the values for this test
        $run->{full_section_name} = $section;
        $run->{simple_section_name} = $section;
        $run->{simple_section_name} =~ s/^\s*test run:\s*//;
        $run->{analyze_module} = $ret->{analyze_module};
        
        $run->{test_build_simple_section_name} = $test_build->{simple_section_name};

        # Setup some globals
        $MTT::Test::Run::test_executable = $run->{executable};
        $MTT::Test::Run::test_argv = $run->{argv};
        my $all_np = MTT::Values::EvaluateString($run->{np});
        
        # Just one np, or an array of np values?
        if (ref($all_np) eq "") {
            $test_results->{$all_np} =
                _run_one_np($install_dir, $run, $mpi_details, $all_np, $force);
        } else {
            foreach my $this_np (@$all_np) {
                $test_results->{$this_np} =
                    _run_one_np($install_dir, $run, $mpi_details, $this_np,
                                $force);
            }
        }
        ++$count;

        # Write out the "to be saved" test run results
        MTT::Test::SaveRuns($runs_data_dir);
        
        # Output a progress bar
        if ($verbose_out > 50) {
            $verbose_out = 0;
            my $per = sprintf("%d%%", $count / $total * 100);
            $printed = 1;
            Verbose("   ### Test progress: $count of $total section tests complete ($per)\n");
        }
    }
    Verbose("   ### Test progress: $count of $total section tests complete (100%)\n")
        if (!$printed);

    # If we ran any tests at all, then run the after_all step and
    # submit the results to the Reporter
    if (exists($mpi_details->{ran_some_tests})) {
        _run_step($mpi_details, "after_all");
        
        MTT::Reporter::QueueSubmit();
    }
}

sub _run_one_np {
    my ($install_dir, $run, $mpi_details, $np, $force) = @_;

    my $name;
    if (-e $MTT::Test::Run::test_executable) {
        $name = basename($MTT::Test::Run::test_executable);
    }
    $run->{name} = $name;

    # Load up the final global
    $MTT::Test::Run::test_np = $np;

    # Is this np ok for this test?
    my $ok = MTT::Values::EvaluateString($run->{np_ok});
    if ($ok) {

        # Get all the exec's for this one np
        my $execs = MTT::Values::EvaluateString($mpi_details->{exec});

        # If we just got one, run it.  Otherwise, loop over running them.
        if (ref($execs) eq "") {
            _run_one_test($install_dir, $run, $mpi_details, $execs, $name, 1,
                          $force);
        } else {
            my $variant = 1;
            foreach my $e (@$execs) {
                _run_one_test($install_dir, $run, $mpi_details, $e, $name,
                              $variant++, $force);
            }
        }
    }
}

sub _run_one_test {
    my ($install_dir, $run, $mpi_details, $cmd, $name, $variant, $force) = @_;

    # Have we run this test already?  Wow, Perl sucks sometimes -- you
    # can't check for the entire thing because the very act of
    # checking will bring all the intermediary hash levels into
    # existence if they didn't already exist.

    my $basename;
    if (-e $MTT::Test::Run::test_executable) {
        $basename = basename($MTT::Test::Run::test_executable);
    }

    my $str = "   Test: " . $basename .
        ", np=$MTT::Test::Run::test_np, variant=$variant:";

    if (!$force &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}->{$run->{simple_section_name}}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}->{$run->{simple_section_name}}->{$name}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}->{$run->{simple_section_name}}->{$name}->{$MTT::Test::Run::test_np}) &&
        exists($MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}->{$run->{simple_section_name}}->{$name}->{$MTT::Test::Run::test_np}->{$cmd})) {
        Verbose("$str Skipped (already ran)\n");
        ++$verbose_out;
        return;
    }

    # Setup some environment variables for steps
    delete $ENV{MTT_TEST_NP};
    $ENV{MTT_TEST_PREFIX} = $MTT::Test::Run::test_prefix;
    if (MTT::Values::Functions::have_hostfile()) {
        $ENV{MTT_TEST_HOSTFILE} = MTT::Values::Functions::hostfile();
    } else {
        $ENV{MTT_TEST_HOSTFILE} = "";
    }
    if (MTT::Values::Functions::have_hostlist()) {
        $ENV{MTT_TEST_HOSTLIST} = MTT::Values::Functions::hostlist();
    } else {
        $ENV{MTT_TEST_HOSTLIST} = "";
    }

    # See if we need to run the before_all step.
    if (! exists($mpi_details->{ran_some_tests})) {
        _run_step($mpi_details, "before_any");
    }
    $mpi_details->{ran_some_tests} = 1;

    # If there is a before_each step, run it
    $ENV{MTT_TEST_NP} = $MTT::Test::Run::test_np;
    _run_step($mpi_details, "before_each");

    my $timeout = MTT::Values::EvaluateString($run->{timeout});
    my $out_lines = MTT::Values::EvaluateString($run->{stdout_save_lines});
    my $err_lines = MTT::Values::EvaluateString($run->{stderr_save_lines});
    my $merge = MTT::Values::EvaluateString($run->{merge_stdout_stderr});
    my $start_time = time;
    $run->{start} = timegm(gmtime());

    my $x = MTT::DoCommand::Cmd($merge, $cmd, $timeout, $out_lines, $err_lines);

    my $stop_time = time;
    $run->{stop} = timegm(gmtime());
    $run->{duration} = $stop_time - $start_time . " seconds";
    $run->{np} = $MTT::Test::Run::test_np;
    $run->{cmd} = $cmd;

    $MTT::Test::Run::test_exit_status = $x->{exit_status};

    # Analyze the test parameters and results
    my $report;
    $report = MTT::Module::Run("MTT::Test::Analyze", "Analyze", $run, $mpi_details, $str, $x);
    $report->{variant} = $variant;
    # Assume that the Analyze module will output one line
    ++$verbose_out;

    # For Test Runs data, we have two datasets: the "to be saved" set
    # and the "all results" set.  The "to be saved" set is a
    # relatively small set of data that is written out to disk
    # periodically (i.e., augmenting what has already been written
    # out).  The "all results" set is everything that has occurred so
    # far.  We do this because the "all results" set can get *very*
    # large, so we don't want to write out the whole thing every time
    # we save the results to disk.

    # So save this new result in both the "to be saved" and "all
    # results" sets.  We'll write out the "to be saved" results
    # shortly.

    $MTT::Test::runs_to_be_saved->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}->{$run->{simple_section_name}}->{$name}->{$MTT::Test::Run::test_np}->{$cmd} = 
        $MTT::Test::runs->{$mpi_details->{mpi_get_simple_section_name}}->{$mpi_details->{version}}->{$mpi_details->{mpi_install_simple_section_name}}->{$run->{test_build_simple_section_name}}->{$run->{simple_section_name}}->{$name}->{$MTT::Test::Run::test_np}->{$cmd} = $report;
    MTT::Reporter::QueueAdd("Test Run", $run->{simple_section_name}, $report);

    # If there is an after_each step, run it
    $ENV{MTT_TEST_RUN_RESULT} = 
        (MTT::Values::PASS == $report->{test_result} ? "passed" :
         (MTT::Values::FAIL == $report->{test_result} ? "failed" :
          (MTT::Values::SKIPPED == $report->{test_result} ? "skipped" :
           (MTT::Values::TIMED_OUT == $report->{test_result} ? "timed_out" : "unknown"))));
    _run_step($mpi_details, "after_each");
    delete $ENV{MTT_TEST_RUN_RESULT};

    return $run->{pass};
}

sub _run_step {
    my ($mpi_details, $step) = @_;

    $step .= "_exec";
    if (exists($mpi_details->{$step}) && $mpi_details->{$step}) {
        Debug("Running step: $step\n");
        my $x = MTT::DoCommand::CmdScript(1, $mpi_details->{$step}, 10);
        if ($x->{timed_out}) {
            Verbose("  Warning: step $step TIMED OUT\n");
            Verbose("  Output: $x->{stdout}\n")
                if (defined($x->{stdout}) && $x->{stdout} ne "");
        } elsif (MTT::DoCommand::wifsignaled($x->{exit_status})) {
            my $ret = MTT::DoCommand::wtermsig($x->{exit_status});
            Verbose("  Warning: step $step finished via signal $ret; skipping\n");
            Verbose("  Output: $x->{stdout}\n")
                if (defined($x->{stdout}) && $x->{stdout} ne "");
        } elsif (!MTT::DoCommand::wsuccess($x->{exit_status})) {
            my $success = MTT::DoCommand::wsuccess($x->{exit_status});
            my $exited = MTT::DoCommand::wifexited($x->{exit_status});
            my $exit_value = MTT::DoCommand::wexitstatus($x->{exit_status});
            Verbose("  Warning: step $step ($x->{exit_status} : success $success : exited $exited) finished with nonzero exit status ($exit_value)\n");
            Verbose("  Output: $x->{stdout}\n")
                if (defined($x->{stdout}) && $x->{stdout} ne "");
        }
    }
}

1;
