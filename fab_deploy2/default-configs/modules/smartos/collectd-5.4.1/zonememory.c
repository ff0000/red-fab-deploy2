/**
 * Copied from collectd - src/memory.c and modified by RED Interactive
 * to report zone specific information
 *
 * Copyright (C) 2005-2008  Florian octo Forster
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
 *   Simon Kuhnle <simon at blarzwurst.de>
 *   Manuel Sanmartin
 **/

#include "collectd.h"
#include "common.h"
#include "plugin.h"


static kstat_t *ksp;

static int memory_init (void)
{

    if (get_kstat (&ksp, "memory_cap", -1, NULL) != 0)
    {
	    ksp = NULL;
	    return (-1);
    }
    return(0);
}

static void memory_submit (const char *type_instance, gauge_t value)
{
	value_t values[1];
	value_list_t vl = VALUE_LIST_INIT;

	values[0].gauge = value;

	vl.values = values;
	vl.values_len = 1;
	sstrncpy (vl.host, hostname_g, sizeof (vl.host));
	sstrncpy (vl.plugin, "zonememory", sizeof (vl.plugin));
	sstrncpy (vl.type, "memory", sizeof (vl.type));
	sstrncpy (vl.type_instance, type_instance, sizeof (vl.type_instance));

	plugin_dispatch_values (&vl);
}

static int memory_read (void)
{
	/* Modified to only read zone info should not be run outside of a zone */
	long long mem_used;
	long long mem_free;
	long long physmem;

	if (ksp == NULL)
		return (-1);

	mem_used = get_kstat_value (ksp, "rss");
	physmem = get_kstat_value (ksp, "physcap");

	mem_free = physmem - mem_used;
	memory_submit ("used",   mem_used);
	memory_submit ("free",   mem_free);

	return (0);
}

void module_register (void)
{
	plugin_register_init ("zonememory", memory_init);
	plugin_register_read ("zonememory", memory_read);
} /* void module_register */
