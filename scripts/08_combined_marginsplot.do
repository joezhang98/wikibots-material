/*
  Script 08: Margins Computation
  --------------------------------
  Re-estimates the main regression (Model 1: all combined) for each of the
  five quality levels, then computes predicted margins at a 3×3 grid of
  bot-edit and human-edit levels (low/medium/high = −1 SD / mean / +1 SD).
  Output is used by 10_combined_figure.py to draw the margins heatmap panel.

  Input:  processed/project_month_panel.dta
  Output: processed/margins_interaction_data.csv
*/

clear all
frames reset
set scheme s1color

* Colors match the Python figure palette (09_dual_axis_timeline.py, 10_combined_figure.py)
* Blue:   #4C72B0 ->  76 114 176
* Orange: #DD8452 -> 221 132  82
global COL_BLUE   "76 114 176"
global COL_ORANGE "221 132 82"
global COL_GRAY   "150 150 150"

global WIKIBOTS_SC "`c(pwd)'"
use "$WIKIBOTS_SC/processed/project_month_panel.dta", clear

/*First loop : margins plots for talk interaction only */
/*Second loop: margins plots for talk and wp interaction */

capture label variable art_page_bot_revs_log_std      "Bot article edits"
capture label variable art_page_bot_nbd_revs_log_std  "Bot article edits (NBD)"
capture label variable aa_bot_op_maj_revs_log_std     "Bot: Operational"
capture label variable aa_bot_ex_maj_revs_log_std     "Bot: Exception Management"
capture label variable aa_bot_td_maj_revs_log_std     "Bot: Task Division"
capture label variable aa_bot_ta_maj_revs_log_std     "Bot: Task Allocation"
capture label variable aa_bot_ip_maj_revs_log_std     "Bot: Information Provision"
capture label variable human_revs_log_std       	  "Human edits"
capture label variable art_talk_human_revs_log_std    "Human article talk edits"
capture label variable art_page_human_revs_log_std    "Human article edits"
capture label variable wp_human_revs_log_std          "Human WikiProject edits"
capture label variable wp_size_log                    "WikiProject size (log)"
capture label variable wp_days_created_log            "WikiProject age (days, log)"
capture label variable qual_fa_log                    "Quality FA dummy"
capture label variable qual_ga_log                    "Quality GA dummy"
capture label variable qual_a_log                     "Quality A dummy"
capture label variable qual_b_log                     "Quality B dummy"
capture label variable qual_c_log                     "Quality C dummy"
capture label variable qual_start_log                 "Quality START dummy"
capture label variable qual_stub_log                  "Quality STUB dummy"
capture label variable art_bot_revs_log_std 	"Bot Edits"
capture label variable human_revs_log_std 	"Human Edits"

global control_vars "qual_a_any_log qual_b_log qual_c_log qual_start_log qual_stub_log wp_size_log wp_days_created_log art_page_human_revs_log_std "

/* Loop over dependent variables (qualities) */
local dvs "stub start c b a"
local first_plot 1

* Create empty frame for collecting margins data
frame create margins_data
frame margins_data: gen str10 quality = ""
frame margins_data: gen bot_level = .
frame margins_data: gen human_level = .
frame margins_data: gen margin = .
frame margins_data: gen se = .
frame margins_data: gen ci_lower = .
frame margins_data: gen ci_upper = .

foreach dv of local dvs {

    di "\n==== Running model for DV = `dv' ====\n"

    reghdfe F.qual_`dv'_gte_delta_log ///
	c.art_bot_revs_log_std c.human_revs_log_std c.art_bot_revs_log_std#c.human_revs_log_std ///
	$control_vars , absorb(wp_id month_count) cluster(wp_id)

    * Overall margins (no per-bot loop)
    di "Running overall margins (interaction)"
    margins, at(art_bot_revs_log_std = (-1 0 1) human_revs_log_std = (-1 0 1))

	* Export margins data for Python plotting
	matrix b = r(b)
	matrix V = r(V)
	local nmargins = colsof(b)

	* at() values: bot = (-1,0,1) crossed with human = (-1,0,1)
	* Order: bot=-1,human=-1; bot=0,human=-1; bot=1,human=-1; bot=-1,human=0; ...
	local bot_vals   "-1 0 1 -1 0 1 -1 0 1"
	local human_vals "-1 -1 -1 0 0 0 1 1 1"

	forvalues i = 1/`nmargins' {
		local bot_val : word `i' of `bot_vals'
		local human_val : word `i' of `human_vals'
		local margin_est = b[1,`i']
		local margin_se = sqrt(V[`i',`i'])
		local ci_lo = `margin_est' - 1.96 * `margin_se'
		local ci_hi = `margin_est' + 1.96 * `margin_se'

		frame post margins_data ("`dv'") (`bot_val') (`human_val') (`margin_est') (`margin_se') (`ci_lo') (`ci_hi')
	}
	* Save Names with capital letters
	local large_dv = strupper("`dv'")
	display "`large_dv'"
	if `first_plot'==1 {
		marginsplot, allsimplelabels name(mplot_`dv'_overall_talk, replace) ///
			legend(position(7) ring(0) title("Human edits", size(small)) region(lcolor(none) fcolor(none))) title("`large_dv'") ///
			ysc(r(0 3)) ylabel(0(.5)3, nogrid) ///
			yline(0, lcolor(gs12) lpattern(dash)) ///
			plot1opts(lcolor("${COL_BLUE}") mcolor("${COL_BLUE}") lwidth(medthick) msymbol(O) msize(medsmall)) ///
			plot2opts(lcolor("${COL_GRAY}") mcolor("${COL_GRAY}") lwidth(medthick) msymbol(O) msize(medsmall)) ///
			plot3opts(lcolor("${COL_ORANGE}") mcolor("${COL_ORANGE}") lwidth(medthick) msymbol(O) msize(medsmall)) ///
			ci1opts(lcolor("${COL_BLUE}") lwidth(thin)) ///
			ci2opts(lcolor("${COL_GRAY}") lwidth(thin)) ///
			ci3opts(lcolor("${COL_ORANGE}") lwidth(thin)) ///
			graphregion(color(white)) plotregion(color(white))
			local first_plot 0
	}
	else {
		marginsplot, allsimplelabels name(mplot_`dv'_overall_talk, replace) ///
			legend(off) title("`large_dv'") ///
			ysc(r(0 3)) ytitle("") ylabel(0(.5)3, nogrid) ///
			yline(0, lcolor(gs12) lpattern(dash)) ///
			plot1opts(lcolor("${COL_BLUE}") mcolor("${COL_BLUE}") lwidth(medthick) msymbol(O) msize(medsmall)) ///
			plot2opts(lcolor("${COL_GRAY}") mcolor("${COL_GRAY}") lwidth(medthick) msymbol(O) msize(medsmall)) ///
			plot3opts(lcolor("${COL_ORANGE}") mcolor("${COL_ORANGE}") lwidth(medthick) msymbol(O) msize(medsmall)) ///
			ci1opts(lcolor("${COL_BLUE}") lwidth(thin)) ///
			ci2opts(lcolor("${COL_GRAY}") lwidth(thin)) ///
			ci3opts(lcolor("${COL_ORANGE}") lwidth(thin)) ///
			graphregion(color(white)) plotregion(color(white))
	}
    //capture noisily graph export "$WIKIBOTS_SC/results/figures/margins_overall_`dv'_all.png", replace width(1200)
}

/* TALK: bots as rows (rows = bots, cols = quals) */
local comb_list_talk_bxr ""
foreach dv of local dvs {
	local comb_list_talk_bxr "`comb_list_talk_bxr' mplot_`dv'_overall_talk"
}
graph combine `comb_list_talk_bxr', cols(5) imargin(zero) ysize(4) xsize(12) ///
	name(margins_talk_grid_bxr, replace) title("") graphregion(color(white))

* Export margins data for Python plotting
frame margins_data: export delimited using "$WIKIBOTS_SC/processed/margins_interaction_data.csv", replace
di "Margins data exported to processed/margins_interaction_data.csv"
