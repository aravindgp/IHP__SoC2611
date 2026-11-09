puts "PROBE set_macro_extension: [info commands set_macro_extension]"
puts "PROBE drt::step_dr: [info commands drt::step_dr]"
puts "PROBE drt::step_end: [info commands drt::step_end]"
puts "PROBE detailed_route_num_drvs: [info commands detailed_route_num_drvs]"
if {[catch {detailed_route -help} e]} { puts "PROBE detailed_route -help: $e" }
