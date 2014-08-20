/**
 * Copied from collectd - src/cpu.c and modified by RED Interactive
 * to report zone specific information
 *
 * Copyright (C) 2005-2010  Florian octo Forster
 * Copyright (C) 2008       Oleg King
 * Copyright (C) 2009       Simon Kuhnle
 * Copyright (C) 2009       Manuel Sanmartin
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; only version 2 of the License is applicable.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
 *
 * Authors:
 *   Florian octo Forster <octo at verplant.org>
 *   Oleg King <king2 at kaluga.ru>
 *   Simon Kuhnle <simon at blarzwurst.de>
 *   Manuel Sanmartin
 **/

#include "collectd.h"
#include "common.h"
#include "plugin.h"
#include <zone.h>

static kstat_t *ksp;

static int init (void)
{
    int zid;
    int size;
    zid = (int)getzoneid();

    size = snprintf(NULL, 0, "cpucaps_zone_%d", zid);
    char stat_name[size+1];
    snprintf(stat_name, size+1, "cpucaps_zone_%d", zid);
    if (get_kstat (&ksp, "caps", zid, stat_name) != 0)
    {
	    ksp = NULL;
	    return (-1);
    }
	return (0);
} /* int init */

static void submit (int cpu_num, const char *type_instance, gauge_t value)
{
	value_t values[1];
	value_list_t vl = VALUE_LIST_INIT;

	values[0].gauge = value;

	vl.values = values;
	vl.values_len = 1;
	sstrncpy (vl.host, hostname_g, sizeof (vl.host));
	sstrncpy (vl.plugin, "zonecpu", sizeof (vl.plugin));
	ssnprintf (vl.plugin_instance, sizeof (vl.plugin_instance),
			"%i", cpu_num);
	sstrncpy (vl.type, "cpu", sizeof (vl.type));
	sstrncpy (vl.type_instance, type_instance, sizeof (vl.type_instance));

	plugin_dispatch_values (&vl);
}

static int cpu_read (void)
{

	long long usage;
	long long nwait;

	if (ksp == NULL)
		return (-1);

	nwait = get_kstat_value (ksp, "nwait");
	usage = get_kstat_value (ksp, "usage");

	submit (0, "nwait", nwait);
	submit (0, "usage", usage);

	return (0);
}

void module_register (void)
{
	plugin_register_init ("zonecpu", init);
	plugin_register_read ("zonecpu", cpu_read);
} /* void module_register */
