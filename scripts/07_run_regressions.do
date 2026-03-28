/*
  Script 07: Regressions and Table Export
  -----------------------------------------
  Runs nine model specifications using reghdfe (high-dimensional fixed effects)
  with WikiProject and month FEs, clustered standard errors at WikiProject level.
  Exports regression tables (.rtf and .tex) and coefficient CSVs used by
  the Python figure scripts.

  Input:  processed/project_month_panel.dta
  Output: results/tables/*.{rtf,tex}
          processed/coef_*.csv
          processed/descriptives.csv
*/

clear all
frames reset
set scheme s1color
global WIKIBOTS_NEW "`c(pwd)'"
use "$WIKIBOTS_NEW/processed/project_month_panel.dta", clear

* Different quality levels
local LOCAL_QUAL_CAT "stub start c b a" // ga b

label variable art_talk_human_revs_log_std "Human Talk Edits"
label variable art_page_human_revs_log_std "Human Article Edits"
label variable wp_human_revs_log_std "Human WP Edits"
label variable human_revs_log_std "Human Coordination Edits"
label variable human_revs_log "Human Coord. Edits (log)"

label variable aa_bot_op_maj_revs_log_std "Bot Edits (Operation)"
label variable aa_bot_ex_maj_revs_log_std "Bot Edits (Exception)"
label variable aa_bot_coord_maj_revs_log_std "Bot Edits (Coordination)"
label variable art_bot_revs_log_std "Bot Edits"

global control_vars "qual_a_any_log qual_b_log qual_c_log qual_start_log qual_stub_log wp_size_log wp_days_created_log art_page_human_revs_log_std "

* Calculate descriptive statistics for key variables
estpost summarize ///
	art_talk_human_revs_log ///
	wp_human_revs_log ///
	aa_bot_op_maj_revs_log ///
	aa_bot_ex_maj_revs_log ///
	aa_bot_coord_maj_revs_log

esttab using "$WIKIBOTS_NEW/processed/descriptives.csv", ///
	cells("mean(fmt(a2))") ///
	unstack nogaps replace

*************** Baseline Interaction, all combined
*********************************************************************
frame change default


matrix coeffs_qual_talk = J(5,6,.)

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	reghdfe F.qual_`qual'_gte_delta_log ///
	c.art_bot_revs_log_std c.human_revs_log_std c.art_bot_revs_log_std#c.human_revs_log_std ///
	$control_vars , absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

	* Store interaction coefficient + SE
	matrix coeffs_qual_talk[`i',1] = _b[c.art_bot_revs_log_std#c.human_revs_log_std]
	matrix coeffs_qual_talk[`i',2] = _se[c.art_bot_revs_log_std#c.human_revs_log_std]

	* Store main effect for bot edits + SE
	matrix coeffs_qual_talk[`i',3] = _b[c.art_bot_revs_log_std]
	matrix coeffs_qual_talk[`i',4] = _se[c.art_bot_revs_log_std]

	* Store main effect for talk edits + SE
	matrix coeffs_qual_talk[`i',5] = _b[c.human_revs_log_std]
	matrix coeffs_qual_talk[`i',6] = _se[c.human_revs_log_std]

}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/1_all_combined.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/1_all_combined.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)


***************************************************
* Plot Talk Interaction
***************************************************
frame create frame_6
frame change frame_6
svmat double coeffs_qual_talk, names(col)
rename c1 b_interaction
rename c2 se_interaction
rename c3 b_bot
rename c4 se_bot
rename c5 b_talk
rename c6 se_talk
gen number = _n
gen ub_interaction = b_interaction + 1.96*se_interaction
gen lb_interaction = b_interaction - 1.96*se_interaction

gen ub_bot = b_bot + 1.96*se_bot
gen lb_bot = b_bot - 1.96*se_bot

gen ub_talk = b_talk + 1.96*se_talk
gen lb_talk = b_talk - 1.96*se_talk

export delimited using "$WIKIBOTS_NEW/processed/coef_1_all_combined.csv", replace

frame change default



*************** Bot combined, talk and art separated *******************************
********************************************************************************

matrix coeffs_qual_talk = J(5,4,.)

local i = 0
foreach qual of local LOCAL_QUAL_CAT {

	reghdfe F.qual_`qual'_gte_delta_log ///
		c.art_bot_revs_log_std c.art_talk_human_revs_log_std c.wp_human_revs_log_std ///
		c.art_bot_revs_log_std#c.art_talk_human_revs_log_std ///
		c.art_bot_revs_log_std#c.wp_human_revs_log_std ///
		$control_vars , absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

	local ++i
	matrix coeffs_qual_talk[`i',1] = _b[c.art_bot_revs_log_std#c.art_talk_human_revs_log_std]
	matrix coeffs_qual_talk[`i',2] = _se[c.art_bot_revs_log_std#c.art_talk_human_revs_log_std]
	matrix coeffs_qual_talk[`i',3] = _b[c.art_bot_revs_log_std#c.wp_human_revs_log_std]
	matrix coeffs_qual_talk[`i',4] = _se[c.art_bot_revs_log_std#c.wp_human_revs_log_std]
}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/2_talk_and_art_sep.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")


esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/2_talk_and_art_sep.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)


***************************************************
* Plot Talk Interaction
***************************************************
frame create frame_10
frame change frame_10
svmat double coeffs_qual_talk, names(col)
rename c1 b_art
rename c2 se_art
rename c3 b_wp
rename c4 se_wp
gen number = _n

gen ub_art = b_art + 1.96*se_art
gen lb_art = b_art - 1.96*se_art

gen ub_wp = b_wp + 1.96*se_wp
gen lb_wp = b_wp - 1.96*se_wp

export delimited using "$WIKIBOTS_NEW/processed/coef_2_talk_and_art_sep.csv", replace

frame change default



*************** Bot types, talk and art combined *******************************
********************************************************************************

local BOT_CATS "aa_bot_op_maj_revs_log_std aa_bot_ex_maj_revs_log_std aa_bot_coord_maj_revs_log_std"

matrix coeffs_qual_talk = J(15,2,.)

local i = 0
foreach qual of local LOCAL_QUAL_CAT {

    reghdfe F.qual_`qual'_gte_delta_log ///
        c.aa_bot_op_maj_revs_log_std c.aa_bot_ex_maj_revs_log_std c.aa_bot_coord_maj_revs_log_std ///
        c.human_revs_log_std ///
        c.aa_bot_op_maj_revs_log_std#c.human_revs_log_std ///
        c.aa_bot_ex_maj_revs_log_std#c.human_revs_log_std ///
        c.aa_bot_coord_maj_revs_log_std#c.human_revs_log_std ///
        $control_vars , absorb(wp_id month_count) cluster(wp_id)
    estimates store `qual', title("`qual'")


    foreach bot of local BOT_CATS {
        local ++i
        matrix coeffs_qual_talk[`i',1] = _b[c.`bot'#c.human_revs_log_std]
        matrix coeffs_qual_talk[`i',2] = _se[c.`bot'#c.human_revs_log_std]

    }
}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/3_bot_type_art_and_talk_coord.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/3_bot_type_art_and_talk_coord.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)


***************************************************
* Plot Talk Interaction
***************************************************
frame create frame_9
frame change frame_9
svmat double coeffs_qual_talk, names(col)
rename c1 b
rename c2 se
gen number = _n
gen bot = ""
gen qual = ""

local quals "stub start c b a"
local bots  "op ex coord"   // short names; match whatever labels you want

local r = 1
foreach q of local quals {
    foreach b of local bots {
        replace qual = "`q'" in `r'
        replace bot  = "`b'" in `r'
        local ++r
    }
}

gen ub = b + 1.96*se
gen lb = b - 1.96*se
export delimited using "$WIKIBOTS_NEW/processed/coef_3_bot_type_art_and_talk_coord.csv", replace

frame change default



*************** Baseline Interaction with _log (not standardized)
*********************************************************************
frame change default


matrix coeffs_qual_talk = J(5,6,.)

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	reghdfe F.qual_`qual'_gte_delta_log ///
	c.art_bot_revs_log c.human_revs_log c.art_bot_revs_log#c.human_revs_log ///
	$control_vars , absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

	* Store interaction coefficient + SE
	matrix coeffs_qual_talk[`i',1] = _b[c.art_bot_revs_log#c.human_revs_log]
	matrix coeffs_qual_talk[`i',2] = _se[c.art_bot_revs_log#c.human_revs_log]

	* Store main effect for bot edits + SE
	matrix coeffs_qual_talk[`i',3] = _b[c.art_bot_revs_log]
	matrix coeffs_qual_talk[`i',4] = _se[c.art_bot_revs_log]

	* Store main effect for talk edits + SE
	matrix coeffs_qual_talk[`i',5] = _b[c.human_revs_log]
	matrix coeffs_qual_talk[`i',6] = _se[c.human_revs_log]

}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_1_all_combined_log.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_1_all_combined_log.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)


***************************************************
* Plot Talk Interaction
***************************************************
frame create frame_6_log
frame change frame_6_log
svmat double coeffs_qual_talk, names(col)
rename c1 b_interaction
rename c2 se_interaction
rename c3 b_bot
rename c4 se_bot
rename c5 b_talk
rename c6 se_talk
gen number = _n
gen ub_interaction = b_interaction + 1.96*se_interaction
gen lb_interaction = b_interaction - 1.96*se_interaction

gen ub_bot = b_bot + 1.96*se_bot
gen lb_bot = b_bot - 1.96*se_bot

gen ub_talk = b_talk + 1.96*se_talk
gen lb_talk = b_talk - 1.96*se_talk

export delimited using "$WIKIBOTS_NEW/processed/coef_rob_1_all_combined_log.csv", replace

frame change default



*************** Baseline Interaction with DV non-log
*********************************************************************
frame change default

matrix coeffs_qual_talk = J(5,6,.)

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	reghdfe F.qual_`qual'_gte_delta ///
	c.art_bot_revs_log_std c.human_revs_log_std c.art_bot_revs_log_std#c.human_revs_log_std ///
	$control_vars , absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

	* Store interaction coefficient + SE
	matrix coeffs_qual_talk[`i',1] = _b[c.art_bot_revs_log_std#c.human_revs_log_std]
	matrix coeffs_qual_talk[`i',2] = _se[c.art_bot_revs_log_std#c.human_revs_log_std]

	* Store main effect for bot edits + SE
	matrix coeffs_qual_talk[`i',3] = _b[c.art_bot_revs_log_std]
	matrix coeffs_qual_talk[`i',4] = _se[c.art_bot_revs_log_std]

	* Store main effect for talk edits + SE
	matrix coeffs_qual_talk[`i',5] = _b[c.human_revs_log_std]
	matrix coeffs_qual_talk[`i',6] = _se[c.human_revs_log_std]

}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_2_dv_non_log.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	order(c.art_bot_revs_log_std c.human_revs_log_std ///
	c.art_bot_revs_log_std#c.human_revs_log_std) ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_2_dv_non_log.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	order(c.art_bot_revs_log_std c.human_revs_log_std ///
	c.art_bot_revs_log_std#c.human_revs_log_std) ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)



*************** Baseline Interaction with more lags
*********************************************************************
frame change default

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	reghdfe F.qual_`qual'_gte_delta_log ///
	c.art_bot_revs_log_std c.l1.art_bot_revs_log_std c.l2.art_bot_revs_log_std  c.l3.art_bot_revs_log_std  c.l4.art_bot_revs_log_std ///
	c.human_revs_log_std c.l1.human_revs_log_std c.l2.human_revs_log_std  c.l3.human_revs_log_std  c.l4.human_revs_log_std ///
	c.art_bot_revs_log_std#c.human_revs_log_std c.l1.art_bot_revs_log_std#c.l1.human_revs_log_std ///
	c.l2.art_bot_revs_log_std#c.l2.human_revs_log_std c.l3.art_bot_revs_log_std#c.l3.human_revs_log_std ///
	c.l4.art_bot_revs_log_std#c.l4.human_revs_log_std ///
	$control_vars , absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_3_lags.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) replace compress label ///
	varlabels( ///
		L.art_bot_revs_log_std  "Bot Edits (t-1)" ///
		L2.art_bot_revs_log_std "Bot Edits (t-2)" ///
		L3.art_bot_revs_log_std "Bot Edits (t-3)" ///
		L4.art_bot_revs_log_std "Bot Edits (t-4)" ///
		L.human_revs_log_std    "Human Coordination Edits (t-1)" ///
		L2.human_revs_log_std   "Human Coordination Edits (t-2)" ///
		L3.human_revs_log_std   "Human Coordination Edits (t-3)" ///
		L4.human_revs_log_std   "Human Coordination Edits (t-4)" ///
		cL.art_bot_revs_log_std#cL.human_revs_log_std   "Bot Edits (t-1) X Human Coordination Edits (t-1)" ///
		cL2.art_bot_revs_log_std#cL2.human_revs_log_std "Bot Edits (t-2) X Human Coordination Edits (t-2)" ///
		cL3.art_bot_revs_log_std#cL3.human_revs_log_std "Bot Edits (t-3) X Human Coordination Edits (t-3)" ///
		cL4.art_bot_revs_log_std#cL4.human_revs_log_std "Bot Edits (t-4) X Human Coordination Edits (t-4)" ///
		_cons Constant ///
	) ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_3_lags.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) replace compress label ///
	varlabels( ///
		L.art_bot_revs_log_std  "Bot Edits\textsubscript{t-1}" ///
		L2.art_bot_revs_log_std "Bot Edits\textsubscript{t-2}" ///
		L3.art_bot_revs_log_std "Bot Edits\textsubscript{t-3}" ///
		L4.art_bot_revs_log_std "Bot Edits\textsubscript{t-4}" ///
		L.human_revs_log_std    "Human Coordination Edits\textsubscript{t-1}" ///
		L2.human_revs_log_std   "Human Coordination Edits\textsubscript{t-2}" ///
		L3.human_revs_log_std   "Human Coordination Edits\textsubscript{t-3}" ///
		L4.human_revs_log_std   "Human Coordination Edits\textsubscript{t-4}" ///
		cL.art_bot_revs_log_std#cL.human_revs_log_std   "Bot Edits\textsubscript{t-1} $\times$ Human Coordination Edits\textsubscript{t-1}" ///
		cL2.art_bot_revs_log_std#cL2.human_revs_log_std "Bot Edits\textsubscript{t-2} $\times$ Human Coordination Edits\textsubscript{t-2}" ///
		cL3.art_bot_revs_log_std#cL3.human_revs_log_std "Bot Edits\textsubscript{t-3} $\times$ Human Coordination Edits\textsubscript{t-3}" ///
		cL4.art_bot_revs_log_std#cL4.human_revs_log_std "Bot Edits\textsubscript{t-4} $\times$ Human Coordination Edits\textsubscript{t-4}" ///
		_cons Constant ///
	) ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)


*************** Baseline Interaction with new/mature WP
*********************************************************************
///wp_stable == 1

frame change default

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	reghdfe F.qual_`qual'_gte_delta_log ///
	c.art_bot_revs_log_std c.human_revs_log_std c.art_bot_revs_log_std#c.human_revs_log_std ///
	$control_vars if wp_stable == 0, absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_4a_growing.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_4a_growing.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

local i = 0
foreach qual of local LOCAL_QUAL_CAT {
	local ++i

	reghdfe F.qual_`qual'_gte_delta_log ///
	c.art_bot_revs_log_std c.human_revs_log_std c.art_bot_revs_log_std#c.human_revs_log_std ///
	$control_vars if wp_stable == 1, absorb(wp_id month_count) cluster(wp_id)
	estimates store `qual', title("`qual'")

}

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_4b_stable.rtf", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " X " ) ///
	nodepvars nonumbers noomitted unstack ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)

estfe `LOCAL_QUAL_CAT', labels(wp_id "WikiProject Fixed Effects" month_count "Month Fixed Effects")

esttab `LOCAL_QUAL_CAT' using "$WIKIBOTS_NEW/results/tables/rob_4b_stable.tex", ///
	mtitles("Stub" "Start" "C" "B" "A+") ///
	cells(b(fmt(%9.3f) star) p(fmt(3) par([ ]))) ///
	stats(r2 r2_within N, fmt(%9.3f %9.0gc) ///
	labels("R-squared overall" "R-squared within" "Observations")) ///
	legend collabels(none) varlabels(_cons Constant) replace compress label ///
	indicate(`r(indicate_fe)') ///
	drop( $control_vars ) ///
	varwidth(20) modelwidth(10) interaction( " $\times$ " ) ///
	nodepvars nonumbers noomitted unstack booktabs ///
	addnotes("Clustered standard errors in parentheses; p-values in brackets.") ///
    starlevels(* 0.10 ** 0.05 *** 0.01)
