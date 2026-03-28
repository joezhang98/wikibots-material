/*
  Script 08b: Relative Importance Analysis
  -----------------------------------------
  Estimates the marginal effects of bot edits, human edits, and their
  interaction for each of the five quality levels, then computes each
  component's share of the total absolute effect.  The output CSV is
  consumed by scripts/11_relative_importance_figure.py.

  Input:  processed/project_month_panel.dta
  Output: processed/relative_importance.csv
*/

clear all
frames reset
set scheme s1color
global WIKIBOTS_NEW "`c(pwd)'"
use "$WIKIBOTS_NEW/processed/project_month_panel.dta", clear

local LOCAL_QUAL_CAT "stub start c b a"

label variable art_talk_human_revs_log_std "Human talk edits"
label variable art_page_human_revs_log_std "Human article edits"
label variable wp_human_revs_log_std        "Human WP edits"
label variable human_revs_log_std           "Human edits"
label variable art_bot_revs_log_std         "Bot edits"

global control_vars "qual_a_any_log qual_b_log qual_c_log qual_start_log qual_stub_log wp_size_log wp_days_created_log art_page_human_revs_log_std"

* Create matrix to store results for each quality level
matrix importance = J(5, 4, .)
matrix colnames importance = bot_effect human_effect interaction_effect quality_level

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	* Bot effect: predicted value at bot +1 SD vs mean (human held at mean)
	reghdfe F.qual_`qual'_gte_delta_log ///
		c.art_bot_revs_log_std c.human_revs_log_std ///
		c.art_bot_revs_log_std#c.human_revs_log_std ///
		$control_vars, absorb(wp_id month_count) cluster(wp_id)

	margins, at(art_bot_revs_log_std=(0 1) human_revs_log_std=0) post
	lincom _b[2._at] - _b[1._at]
	local bot_effect = r(estimate)

	* Human effect: predicted value at human +1 SD vs mean (bot held at mean)
	quietly reghdfe F.qual_`qual'_gte_delta_log ///
		c.art_bot_revs_log_std c.human_revs_log_std ///
		c.art_bot_revs_log_std#c.human_revs_log_std ///
		$control_vars, absorb(wp_id month_count) cluster(wp_id)

	margins, at(art_bot_revs_log_std=0 human_revs_log_std=(0 1)) post
	lincom _b[2._at] - _b[1._at]
	local human_effect = r(estimate)

	* Interaction effect = joint effect minus sum of individual effects
	quietly reghdfe F.qual_`qual'_gte_delta_log ///
		c.art_bot_revs_log_std c.human_revs_log_std ///
		c.art_bot_revs_log_std#c.human_revs_log_std ///
		$control_vars, absorb(wp_id month_count) cluster(wp_id)

	margins, at(art_bot_revs_log_std=(0 1) human_revs_log_std=(0 1)) post
	lincom _b[4._at] - _b[1._at]
	local joint_effect = r(estimate)
	local interaction_effect = `joint_effect' - `bot_effect' - `human_effect'

	matrix importance[`i', 1] = `bot_effect'
	matrix importance[`i', 2] = `human_effect'
	matrix importance[`i', 3] = `interaction_effect'
	matrix importance[`i', 4] = `i'

	display "Quality level: `qual'"
	display "  Bot effect:         `bot_effect'"
	display "  Human effect:       `human_effect'"
	display "  Interaction effect: `interaction_effect'"
	display "  Joint effect:       `joint_effect'"
}

* Convert matrix to dataset
frame create importance_frame
frame change importance_frame
svmat double importance, names(col)

gen qual_label = ""
replace qual_label = "Stub"  if quality_level == 1
replace qual_label = "Start" if quality_level == 2
replace qual_label = "C"     if quality_level == 3
replace qual_label = "B"     if quality_level == 4
replace qual_label = "A+"    if quality_level == 5

* Percentage share of total absolute effect
gen abs_bot         = abs(bot_effect)
gen abs_human       = abs(human_effect)
gen abs_interaction = abs(interaction_effect)
gen total_abs       = abs_bot + abs_human + abs_interaction

gen pct_bot         = (abs_bot         / total_abs) * 100
gen pct_human       = (abs_human       / total_abs) * 100
gen pct_interaction = (abs_interaction / total_abs) * 100

keep qual_label quality_level bot_effect human_effect interaction_effect ///
     pct_bot pct_human pct_interaction

export delimited using "$WIKIBOTS_NEW/processed/relative_importance.csv", replace

list

frame change default
