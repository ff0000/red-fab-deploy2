/**
 * Copied from collectd - src/disk.c and modified by RED Interactive
 * to report zone specific information
 *
 * Copyright (C) 2005-2012  Florian octo Forster
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
 *   Florian octo Forster <octo at collectd.org>
 *   Manuel Sanmartin
 **/

#include "collectd.h"
#include "common.h"
#include "plugin.h"
#include "utils_ignorelist.h"

static kstat_t *ksp;

static int disk_init (void)
{

    if (get_kstat (&ksp, "zone_vfs", -1, NULL) != 0)
    {
	    ksp = NULL;
	    return (-1);
    }
    return(0);
}


static void disk_submit (const char *plugin_instance,
		const char *type,
		derive_t read, derive_t write)
{
	value_t values[2];
	value_list_t vl = VALUE_LIST_INIT;

	values[0].derive = read;
	values[1].derive = write;

	vl.values = values;
	vl.values_len = 2;
	sstrncpy (vl.host, hostname_g, sizeof (vl.host));
	sstrncpy (vl.plugin, "zonevfs", sizeof (vl.plugin));
	sstrncpy (vl.plugin_instance, plugin_instance,
			sizeof (vl.plugin_instance));
	sstrncpy (vl.type, type, sizeof (vl.type));

	plugin_dispatch_values (&vl);
} /* void disk_submit */


static int disk_read (void)
{
	long long reads;
	long long writes;
	long long nreads;
	long long nwrites;
	long long rtime;
	long long wtime;

	if (ksp == NULL)
		return (-1);

	reads = get_kstat_value (ksp, "reads");
	writes = get_kstat_value (ksp, "writes");
	nreads = get_kstat_value (ksp, "nread");
	nwrites = get_kstat_value (ksp, "nwritten");
	rtime = get_kstat_value (ksp, "rtime");
	wtime = get_kstat_value (ksp, "wtime");

	disk_submit ("zonevfs", "disk_octets",
			reads, writes);
	disk_submit ("zonevfs", "disk_ops",
			nreads, nwrites);
	/* FIXME: Convert this to microseconds if necessary */
	disk_submit ("zonevfs", "disk_time",
			rtime, wtime);

	return (0);
} /* int disk_read */

void module_register (void)
{
  plugin_register_init ("zonevfs", disk_init);
  plugin_register_read ("zonevfs", disk_read);
} /* void module_register */
