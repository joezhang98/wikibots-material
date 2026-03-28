/*
  Script 06: Data Preparation
  ----------------------------
  Loads the raw panel CSV, constructs all derived variables used in the
  regressions, and saves the result as a Stata panel dataset.

  Requires: run from repository root (run_data_analysis.py ensures this).
  Input:  data/full_sample_project_level_variables.csv
  Output: processed/project_month_panel.dta
*/

/* Install required SSC packages on first run (requires internet) */
ssc install ftools, replace
ssc install reghdfe, replace
ssc install erepost, replace   /* dependency of estfe, which is called by reghdfe */
ssc install estout, replace
ssc install require, replace
set scheme s1color             /* built-in scheme, works on all Stata 16+ installations */
set more off

/* Set root path from working directory (run_data_analysis.py sets cwd to repo root) */
global WIKIBOTS_NEW "`c(pwd)'"

/* Load data */
clear

import delimited "$WIKIBOTS_NEW/data/full_sample_project_level_variables.csv", case(preserve)
tsset wp_id month_count

/* Remove observations where WikiProject does not exist yet */
drop if wp_days_created == 0
drop if wp_size == 0

/* Log WikiProject size and age variables */
gen wp_size_log = log(wp_size)
label variable wp_size_log "WikiProject Size (log)"
gen wp_days_created_log = log(wp_days_created)
label variable wp_days_created_log "WikiProject Age in Days (log)"

/* Combine human and bot revision counts */
gen wp_human_revs = wp_page_human_revs + wp_talk_human_revs
label variable wp_human_revs "Human WikiProject revisions"
gen human_revs = art_talk_human_revs + wp_page_human_revs + wp_talk_human_revs
label variable human_revs "All human revisions"

gen art_bot_revs = art_page_bot_revs + art_talk_bot_revs
label variable art_bot_revs "Bot article revisions"

/* Create combined A+ quality variable */
gen qual_a_any = qual_fa + qual_ga + qual_a

/* Article quality control variables (log) */
gen qual_a_any_log = log(qual_a_any + 1)
label variable qual_a_any_log "A+ Articles (log)"
gen qual_b_log = log(qual_b + 1)
label variable qual_b_log "B Articles (log)"
gen qual_c_log = log(qual_c + 1)
label variable qual_c_log "C Articles (log)"
gen qual_start_log = log(qual_start + 1)
label variable qual_start_log "Start Articles (log)"
gen qual_stub_log = log(qual_stub + 1)
label variable qual_stub_log "Stub Articles (log)"

/* Create article quality cumulative count variables */
gen qual_a_gte = qual_fa + qual_ga + qual_a
label variable qual_a_gte "Articles A or above"
gen qual_b_gte = qual_fa + qual_ga + qual_a + qual_b
label variable qual_b_gte "Articles B or above"
gen qual_c_gte = qual_fa + qual_ga + qual_a + qual_b + qual_c
label variable qual_c_gte "Articles C or above"
gen qual_start_gte = qual_fa + qual_ga + qual_a + qual_b + qual_c + qual_start
label variable qual_start_gte "Articles Start or above"
gen qual_stub_gte = qual_fa + qual_ga + qual_a + qual_b + qual_c + qual_start + qual_stub
label variable qual_stub_gte "Articles Stub or above"

/* Create article quality change (delta) variables */
bysort wp_id (month_count): gen qual_a_gte_delta = qual_a_gte - L.qual_a_gte
label variable qual_a_gte_delta "Change in A or above"
bysort wp_id (month_count): gen qual_b_gte_delta = qual_b_gte - L.qual_b_gte
label variable qual_b_gte_delta "Change in B or above"
bysort wp_id (month_count): gen qual_c_gte_delta = qual_c_gte - L.qual_c_gte
label variable qual_c_gte_delta "Change in C or above"
bysort wp_id (month_count): gen qual_start_gte_delta = qual_start_gte - L.qual_start_gte
label variable qual_start_gte_delta "Change in Start or above"
bysort wp_id (month_count): gen qual_stub_gte_delta = qual_stub_gte - L.qual_stub_gte
label variable qual_stub_gte_delta "Change in Stub or above"

/* Log-transformed quality delta variables (signed log for negative values) */
foreach cat in a b c start stub {
	gen qual_`cat'_gte_delta_log = 0
	replace qual_`cat'_gte_delta_log = log(qual_`cat'_gte_delta + 1) if qual_`cat'_gte_delta >= 0
	replace qual_`cat'_gte_delta_log = -log(-qual_`cat'_gte_delta + 1) if qual_`cat'_gte_delta < 0
	label variable qual_`cat'_gte_delta_log "Change in `cat' or above (log)"
}

/* Log revision variables */
gen wp_human_revs_log = log(wp_human_revs + 1)
label variable wp_human_revs_log "Human WP edits (log)"
gen human_revs_log = log(human_revs + 1)
label variable human_revs_log "Human edits (log)"
gen art_page_human_revs_log = log(art_page_human_revs + 1)
label variable art_page_human_revs_log "Human article page edits (log)"
gen art_talk_human_revs_log = log(art_talk_human_revs + 1)
label variable art_talk_human_revs_log "Human article talk edits (log)"
gen art_bot_revs_log = log(art_bot_revs + 1)
label variable art_bot_revs_log "Bot article edits (log)"

/* Bot operation and exception categories (majority voting rule), combined article revisions */
gen aa_bot_op_maj_revs = art_page_bot_op_maj_revs + art_talk_bot_op_maj_revs
label variable aa_bot_op_maj_revs "Bot op maj article revisions"
gen aa_bot_op_maj_revs_log = log(aa_bot_op_maj_revs + 1)
label variable aa_bot_op_maj_revs_log "Bot op maj article edits (log)"

gen aa_bot_ex_maj_revs = art_page_bot_ex_maj_revs + art_talk_bot_ex_maj_revs
label variable aa_bot_ex_maj_revs "Bot ex maj article revisions"
gen aa_bot_ex_maj_revs_log = log(aa_bot_ex_maj_revs + 1)
label variable aa_bot_ex_maj_revs_log "Bot ex maj article edits (log)"

/* Coordination bots (IP+TA+TD, majority voting rule), combined article + WikiProject revisions */
gen aa_bot_coord_maj_revs = ///
	art_page_bot_ip_maj_revs + art_page_bot_ta_maj_revs + art_page_bot_td_maj_revs + ///
	art_talk_bot_ip_maj_revs + art_talk_bot_ta_maj_revs + art_talk_bot_td_maj_revs + ///
	wp_page_bot_ip_maj_revs + wp_page_bot_ta_maj_revs + wp_page_bot_td_maj_revs + ///
	wp_talk_bot_ip_maj_revs + wp_talk_bot_ta_maj_revs + wp_talk_bot_td_maj_revs
label variable aa_bot_coord_maj_revs "Bot coord maj all revisions"
gen aa_bot_coord_maj_revs_log = log(aa_bot_coord_maj_revs + 1)
label variable aa_bot_coord_maj_revs_log "Bot coord maj all edits (log)"

/* Standardized revision variables */
foreach var in art_page_human_revs_log art_talk_human_revs_log art_bot_revs_log ///
	wp_human_revs_log human_revs_log ///
	aa_bot_op_maj_revs_log aa_bot_ex_maj_revs_log aa_bot_coord_maj_revs_log {
	egen `var'_std = std(`var')
	label variable `var'_std "`var' (standardized)"
}

/* WikiProject growth and stability (for split-sample robustness checks) */
by wp_id (month_count): egen wp_max_size = max(wp_size)
gen wp_stable = 0
replace wp_stable = 1 if wp_size > 0.9 * wp_max_size
label variable wp_stable "WikiProject stable (>90% max size)"

/* Drop intermediate variables used only for compilation */
drop wp_human_revs qual_a_any ///
	qual_a_gte qual_b_gte qual_c_gte qual_start_gte qual_stub_gte ///
	art_page_human_revs_log ///
	aa_bot_op_maj_revs aa_bot_ex_maj_revs aa_bot_coord_maj_revs ///
	wp_max_size

save "$WIKIBOTS_NEW/processed/project_month_panel.dta", replace
