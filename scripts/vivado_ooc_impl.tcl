# Vivado out-of-context implementation for Chapter 4 RTL tops.
#
# Called by scripts/run_vivado_ooc_impl.py.
#
# Tcl args:
#   top part period_ns out_dir addr_width depth due_tracker_entries max_control_age_cycles

if {$argc < 8} {
    puts "ERROR: expected args: top part period_ns out_dir addr_width depth due_tracker_entries max_control_age_cycles"
    exit 2
}

set top                    [lindex $argv 0]
set part                   [lindex $argv 1]
set period_ns              [lindex $argv 2]
set out_dir                [lindex $argv 3]
set addr_width             [lindex $argv 4]
set depth                  [lindex $argv 5]
set due_tracker_entries    [lindex $argv 6]
set max_control_age_cycles [lindex $argv 7]

file mkdir $out_dir

puts "OOC_START top=$top part=$part period_ns=$period_ns out_dir=$out_dir"

# ---------- Source selection ----------
set sources {}

if {$top eq "period_scheduler"} {
    lappend sources rtl/scrubber/period_scheduler.sv
} elseif {$top eq "scrub_pass_engine"} {
    lappend sources rtl/ecc/secded_32_39_decoder.sv
    lappend sources rtl/scrubber/scrub_pass_engine.sv
} elseif {$top eq "diagnostic_supervisor"} {
    lappend sources rtl/scrubber/diagnostic_supervisor.sv
} elseif {$top eq "adaptive_scrub_controller"} {
    lappend sources rtl/ecc/secded_32_39_decoder.sv
    lappend sources rtl/scrubber/period_scheduler.sv
    lappend sources rtl/scrubber/scrub_pass_engine.sv
    lappend sources rtl/scrubber/diagnostic_supervisor.sv
    lappend sources rtl/scrubber/adaptive_scrub_controller.sv
} elseif {$top eq "measured_error_scrub_controller"} {
    lappend sources rtl/ecc/secded_32_39_decoder.sv
    lappend sources rtl/scrubber/period_scheduler.sv
    lappend sources rtl/scrubber/scrub_pass_engine.sv
    lappend sources rtl/scrubber/diagnostic_supervisor.sv
    lappend sources rtl/scrubber/adaptive_scrub_controller.sv
    lappend sources rtl/scrubber/measured_error_period_estimator.sv
    lappend sources rtl/scrubber/measured_error_scrub_controller.sv
} else {
    puts "ERROR: unsupported top=$top"
    exit 2
}

read_verilog -sv $sources

# ---------- Top-aware generics ----------
set generic_opts {}

if {$top eq "scrub_pass_engine" ||
    $top eq "diagnostic_supervisor" ||
    $top eq "adaptive_scrub_controller" ||
    $top eq "measured_error_scrub_controller"} {
    lappend generic_opts -generic "ADDR_WIDTH=$addr_width"
    lappend generic_opts -generic "DEPTH=$depth"
}

if {$top eq "period_scheduler" ||
    $top eq "adaptive_scrub_controller" ||
    $top eq "measured_error_scrub_controller"} {
    lappend generic_opts -generic "PERIOD_INDEX_WIDTH=4"
    lappend generic_opts -generic "PERIOD0_CYCLES=1"
    lappend generic_opts -generic "PERIOD1_CYCLES=2"
    lappend generic_opts -generic "PERIOD2_CYCLES=5"
    lappend generic_opts -generic "PERIOD3_CYCLES=10"
    lappend generic_opts -generic "PERIOD4_CYCLES=30"
    lappend generic_opts -generic "PERIOD5_CYCLES=60"
    lappend generic_opts -generic "PERIOD6_CYCLES=120"
    lappend generic_opts -generic "PERIOD7_CYCLES=300"
    lappend generic_opts -generic "PERIOD8_CYCLES=600"
    lappend generic_opts -generic "PERIOD9_CYCLES=1200"
    lappend generic_opts -generic "PERIOD10_CYCLES=1800"
    lappend generic_opts -generic "PERIOD11_CYCLES=3600"
    lappend generic_opts -generic "SAFE_PERIOD_INDEX=0"
    lappend generic_opts -generic "MAX_CONTROL_AGE_CYCLES=$max_control_age_cycles"
}

if {$top eq "diagnostic_supervisor"} {
    lappend generic_opts -generic "DUE_TRACKER_ENTRIES=$due_tracker_entries"
}

if {$top eq "adaptive_scrub_controller" ||
    $top eq "measured_error_scrub_controller"} {
    lappend generic_opts -generic "DIAG_DUE_TRACKER_ENTRIES=$due_tracker_entries"
}

puts "OOC_GENERICS $generic_opts"

synth_design -top $top -part $part -mode out_of_context {*}$generic_opts

create_clock -name clk -period $period_ns [get_ports clk]

opt_design
place_design
route_design

set util_file   [file join $out_dir "util_${top}.rpt"]
set timing_file [file join $out_dir "timing_${top}.rpt"]
set power_file  [file join $out_dir "power_${top}.rpt"]

report_utilization    -file $util_file
report_timing_summary -file $timing_file
report_power          -file $power_file

set timing_paths [get_timing_paths -max_paths 1 -setup]
if {[llength $timing_paths] > 0} {
    set wns [get_property SLACK [lindex $timing_paths 0]]
} else {
    set wns "NA"
}

puts "OOC_RESULT top=$top part=$part period_ns=$period_ns wns_ns=$wns util_file=$util_file timing_file=$timing_file power_file=$power_file"

exit
